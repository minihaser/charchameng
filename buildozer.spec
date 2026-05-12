[app]
title = Charchameng
package.name = charchameng
package.domain = uz.kamron.charchameng

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow

orientation = portrait
fullscreen = 0

# Icon va loading ekran
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png

# Android sozlamalari
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Ruxsatlar — tashqi xotira (bor.txt / yoq.txt yozish uchun)
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

# Android 11+ uchun (faylga to'liq kirish)
android.request_legacy_storage = True

# Ekran o'chirilmasin (uzoq skanlash sessiyalari uchun ixtiyoriy)
android.wakelock = False

# Log level (debug uchun 2, release uchun 1)
log_level = 2

[buildozer]
warn_on_root = 1
