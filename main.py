# -*- coding: utf-8 -*-
"""
Marka kodlarini tekshirish — Android APK (KivyMD)
==================================================
PREFIX-MATCH versiyasi:
- Baza fayldagi kodlar yarmida kesilgan (masalan 31 belgi: 01+GTIN+21+serial)
- Skaner to'liq kodni o'qiydi (qo'shimcha 93+cryptokey bilan)
- Tekshirish: skan qilingan kod bazadagi biror kod bilan BOSHLANSA → BOR
- bor.txt / yoq.txt ga TO'LIQ skan qilingan kod yoziladi
- Tezlik: O(K) — K = bazadagi uzunliklar soni (odatda 1-2)
"""

import os
from pathlib import Path
from datetime import datetime

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import platform
from kivy.animation import Animation
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.toast import toast


KV = '''
MDScreen:
    md_bg_color: 0.06, 0.06, 0.08, 1

    MDBoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '8dp'

        # ===== 1) Baza status =====
        MDLabel:
            id: baza_status
            text: "Baza yuklanmagan"
            adaptive_height: True
            theme_text_color: "Custom"
            text_color: 0.78, 0.78, 0.78, 1
            font_style: "Body2"

        MDRaisedButton:
            text: "BAZA YUKLASH (TXT)"
            on_release: app.baza_yuklash_open()
            size_hint_x: 1
            md_bg_color: 0.20, 0.42, 0.72, 1
            font_size: "15sp"

        # ===== 2) Skan input =====
        MDTextField:
            id: kod_input
            hint_text: "Kod (skaner Enter yuboradi)"
            on_text_validate: app.kod_tekshir()
            mode: "line"
            font_size: "18sp"
            multiline: False
            write_tab: False

        MDBoxLayout:
            orientation: 'horizontal'
            spacing: '6dp'
            size_hint_y: None
            height: '44dp'

            MDRaisedButton:
                text: "TEKSHIRISH"
                on_release: app.kod_tekshir()
                size_hint_x: 0.55
                md_bg_color: 0.22, 0.22, 0.28, 1
                font_size: "14sp"

            MDBoxLayout:
                orientation: 'horizontal'
                size_hint_x: 0.45
                spacing: '4dp'

                MDSwitch:
                    id: takror_skip
                    active: False
                    pos_hint: {"center_y": 0.5}

                MDLabel:
                    text: "Takror\\nskip"
                    theme_text_color: "Custom"
                    text_color: 0.65, 0.65, 0.65, 1
                    font_style: "Caption"
                    halign: "left"

        # ===== 3) Natija card =====
        MDCard:
            id: natija_card
            md_bg_color: 0.12, 0.12, 0.14, 1
            padding: '12dp'
            size_hint_y: None
            height: '85dp'
            radius: [12,]

            MDLabel:
                id: natija_label
                text: "Natija: ..."
                font_style: "H4"
                halign: "center"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                bold: True

        # ===== 4) Statistika =====
        MDCard:
            md_bg_color: 0.10, 0.10, 0.12, 1
            padding: '10dp'
            size_hint_y: None
            height: '70dp'
            radius: [10,]

            MDBoxLayout:
                orientation: 'vertical'
                spacing: '2dp'

                MDLabel:
                    id: stat1
                    text: "Baza: 0    Jami skan: 0"
                    theme_text_color: "Custom"
                    text_color: 0.88, 0.88, 0.88, 1
                    font_style: "Body2"
                    bold: True

                MDLabel:
                    id: stat2
                    text: "Bor: 0    Yo'q: 0    Takror: 0"
                    theme_text_color: "Custom"
                    text_color: 0.88, 0.88, 0.88, 1
                    font_style: "Body2"
                    bold: True

        # ===== 5) Tarix sarlavhasi =====
        MDLabel:
            text: "Tarix (oxirgi 300 ta - eng yangisi yuqorida):"
            adaptive_height: True
            theme_text_color: "Custom"
            text_color: 0.55, 0.55, 0.55, 1
            font_style: "Caption"

        # ===== 6) Tarix ro'yxati =====
        ScrollView:
            id: tarix_scroll
            do_scroll_x: False
            bar_width: dp(3)

            MDBoxLayout:
                id: tarix_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '1dp'
                padding: '4dp'

        # ===== 7) Action tugmalar =====
        MDBoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: '40dp'
            spacing: '4dp'

            MDFlatButton:
                text: "Tarix tozalash"
                on_release: app.tarix_tozala()
                theme_text_color: "Custom"
                text_color: 0.75, 0.75, 0.75, 1
                font_size: "12sp"

            MDFlatButton:
                text: "Reset"
                on_release: app.reset_qil()
                theme_text_color: "Custom"
                text_color: 0.95, 0.6, 0.2, 1
                font_size: "12sp"

            Widget:

            MDFlatButton:
                text: "Papka"
                on_release: app.papka_korsat()
                theme_text_color: "Custom"
                text_color: 0.5, 0.75, 1, 1
                font_size: "12sp"
'''


class KodApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.title = "Charchameng"

        # ====== Ma'lumotlar ======
        # Baza: uzunlik bo'yicha guruhlangan set-lar.
        # Misol: {31: {"01...", "01..."}, 25: {"01..."}}
        # Prefix-match: skan[:L] in baza_by_len[L] — O(1) lookup, K = uzunliklar soni.
        self.baza_by_len = {}
        self.baza_uzunliklari = []   # cache: sorted descending [31, 25, ...]
        self.baza_kod_soni = 0       # statistika uchun (umumiy)

        self.skanlangan_kodlar = set()   # to'liq skan qilingan kodlar (takror uchun)
        self.bor_soni = 0
        self.yoq_soni = 0
        self.jami_skanlangan = 0
        self.takror_soni = 0

        self.chiqish_papka = None
        self.bor_fayl = None
        self.yoq_fayl = None

        self.file_manager = MDFileManager(
            exit_manager=self._fm_exit,
            select_path=self._fm_select,
            ext=['.txt'],
        )

        return Builder.load_string(KV)

    def on_start(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ])
            except Exception as e:
                print(f"Permission error: {e}")

        self.chiqish_papka = self._chiqish_papka_aniqla()
        self.bor_fayl = self.chiqish_papka / "bor.txt"
        self.yoq_fayl = self.chiqish_papka / "yoq.txt"

        Clock.schedule_once(lambda dt: self._fokus_qaytarish(), 0.5)

    def _chiqish_papka_aniqla(self):
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                yol = Path(primary_external_storage_path()) / 'Download' / 'KodTekshiruvchi'
            except Exception:
                yol = Path(self.user_data_dir) / 'natijalar'
        else:
            yol = Path.home() / 'KodTekshiruvchi'
        try:
            yol.mkdir(parents=True, exist_ok=True)
        except Exception:
            yol = Path(self.user_data_dir)
        return yol

    # ============== Baza yuklash ==============
    def baza_yuklash_open(self):
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                start = primary_external_storage_path()
            except Exception:
                start = '/'
        else:
            start = str(Path.home())
        try:
            self.file_manager.show(start)
        except Exception as e:
            toast(f"File manager xato: {e}")

    def _fm_exit(self, *args):
        self.file_manager.close()

    def _fm_select(self, path):
        self.file_manager.close()
        self.baza_yukla(path)

    def baza_yukla(self, yol):
        """Faylni o'qib uzunlik bo'yicha guruhlab saqlaydi."""
        try:
            satrlar = None
            for kod_enc in ('utf-8-sig', 'utf-8', 'cp1251', 'latin-1'):
                try:
                    with open(yol, 'r', encoding=kod_enc) as f:
                        satrlar = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue

            if satrlar is None:
                toast("Faylni o'qib bo'lmadi")
                return

            self.baza_by_len.clear()
            self.baza_uzunliklari = []
            self.baza_kod_soni = 0
            takror_baza = 0
            sarlavhalar = 0

            for satr in satrlar:
                k = satr.strip()   # \r, \n, probel — hammasi tozalanadi
                if not k:
                    continue
                if k.startswith('==='):
                    sarlavhalar += 1
                    continue

                L = len(k)
                bucket = self.baza_by_len.get(L)
                if bucket is None:
                    bucket = set()
                    self.baza_by_len[L] = bucket

                if k in bucket:
                    takror_baza += 1
                else:
                    bucket.add(k)
                    self.baza_kod_soni += 1

            # Uzunliklarni uzunroqdan boshlab tartiblaymiz (eng aniq match'ni topish uchun)
            self.baza_uzunliklari = sorted(self.baza_by_len.keys(), reverse=True)

            nom = Path(yol).name
            uzun_info = ", ".join(f"{L}" for L in self.baza_uzunliklari[:5])
            qism = f"{self.baza_kod_soni:,} kod  •  uzunlik: [{uzun_info}]"
            if sarlavhalar:
                qism += f"  •  {sarlavhalar} sarl."
            if takror_baza:
                qism += f"  •  {takror_baza} takror"
            self.root.ids.baza_status.text = f"OK  {nom}  •  {qism}"

            self._stat_yangila()
            toast(f"{self.baza_kod_soni:,} ta kod yuklandi")
            Clock.schedule_once(lambda dt: self._fokus_qaytarish(), 0.2)

        except Exception as e:
            toast(f"Xato: {e}")

    # ============== Asosiy: kod tekshirish ==============
    def _prefix_match(self, skan):
        """
        Skan qilingan kod bazadagi biror kod bilan boshlansa — True qaytaradi.
        Uzunroq prefixdan boshlab tekshiradi (aniqroq match).
        """
        for L in self.baza_uzunliklari:
            if len(skan) >= L:
                if skan[:L] in self.baza_by_len[L]:
                    return True
        return False

    def kod_tekshir(self, *args):
        kod = self.root.ids.kod_input.text.strip()
        self.root.ids.kod_input.text = ""

        if not kod:
            return

        if self.baza_kod_soni == 0:
            toast("Avval baza yuklang!")
            self._fokus_qaytarish()
            return

        self.jami_skanlangan += 1
        vaqt = datetime.now().strftime("%H:%M:%S")

        # Takror tekshirish (to'liq skan qilingan kod bo'yicha)
        takror = kod in self.skanlangan_kodlar
        if takror:
            self.takror_soni += 1
        else:
            self.skanlangan_kodlar.add(kod)

        # ASOSIY: PREFIX-MATCH
        bor_mi = self._prefix_match(kod)

        # Faylga yozish — TO'LIQ skan qilingan kodni
        skip = takror and self.root.ids.takror_skip.active
        yozildi = False
        if not skip:
            try:
                fayl = self.bor_fayl if bor_mi else self.yoq_fayl
                with open(fayl, 'a', encoding='utf-8') as f:
                    f.write(kod + '\n')
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
                yozildi = True
            except Exception as e:
                toast(f"Yozish xatosi: {e}")

        # Hisoblash + UI
        if bor_mi:
            self.bor_soni += 1
            self._natija_korsat("BOR", (0.16, 0.65, 0.30, 1))
        else:
            self.yoq_soni += 1
            self._natija_korsat("YO'Q", (0.80, 0.20, 0.20, 1))

        # Tarixga qatorni qo'shish
        belgi = "[BOR] " if bor_mi else "[YO'Q]"
        suffix = ""
        if takror:
            suffix = "  TAKROR" + ("" if yozildi else " (yozilmadi)")

        # Uzun kodni qisqartirib ko'rsatamiz (tarixda chiroyli bo'lishi uchun)
        ko_kod = kod if len(kod) <= 40 else (kod[:37] + "...")
        matn = f"[{vaqt}]  {belgi}{suffix}   {ko_kod}"
        rang = (0.32, 0.85, 0.45, 1) if bor_mi else (0.95, 0.38, 0.38, 1)
        self._tarixga_qosh(matn, rang)

        self._stat_yangila()
        Clock.schedule_once(lambda dt: self._fokus_qaytarish(), 0.05)

    def _tarixga_qosh(self, matn, rang):
        lst = self.root.ids.tarix_list
        lbl = MDLabel(
            text=matn,
            theme_text_color="Custom",
            text_color=rang,
            font_style="Caption",
            font_size="11sp",
            size_hint_y=None,
            height=dp(20),
        )
        lst.add_widget(lbl)
        while len(lst.children) > 300:
            lst.remove_widget(lst.children[-1])
        self.root.ids.tarix_scroll.scroll_y = 1

    def _natija_korsat(self, matn, rang):
        card = self.root.ids.natija_card
        label = self.root.ids.natija_label
        label.text = matn
        card.md_bg_color = rang
        Animation.cancel_all(card)
        anim = Animation(md_bg_color=(0.12, 0.12, 0.14, 1), duration=0.6, t='out_quad')
        anim.start(card)

    def _fokus_qaytarish(self):
        try:
            self.root.ids.kod_input.focus = True
        except Exception:
            pass

    def _stat_yangila(self):
        self.root.ids.stat1.text = (
            f"Baza: {self.baza_kod_soni:,}    Jami skan: {self.jami_skanlangan:,}"
        )
        self.root.ids.stat2.text = (
            f"Bor: {self.bor_soni:,}    "
            f"Yo'q: {self.yoq_soni:,}    "
            f"Takror: {self.takror_soni:,}"
        )

    # ============== Yordamchi tugmalar ==============
    def tarix_tozala(self):
        self.root.ids.tarix_list.clear_widgets()
        toast("Tarix tozalandi")

    def reset_qil(self):
        self.jami_skanlangan = 0
        self.bor_soni = 0
        self.yoq_soni = 0
        self.takror_soni = 0
        self.skanlangan_kodlar.clear()
        self.root.ids.tarix_list.clear_widgets()
        self.root.ids.natija_label.text = "Natija: ..."
        self._stat_yangila()
        toast("Reset qilindi (fayllarga tegilmadi)")
        self._fokus_qaytarish()

    def papka_korsat(self):
        if self.chiqish_papka:
            toast(f"Papka: {self.chiqish_papka}")


if __name__ == '__main__':
    KodApp().run()
