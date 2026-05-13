[app]
title = Charchameng
package.name = charchameng
package.domain = uz.kamron.charchameng

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

version = 1.0

# Python 3.11 explicitly (default p4a uses 3.14 which breaks kivy 2.3.0)
# kivy 2.3.1 has fixes for newer python; pin everything
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,kivymd==1.2.0,pillow

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

# Ruxsatlar
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

# Android 11+ uchun
android.request_legacy_storage = True

android.wakelock = False

log_level = 2

[buildozer]
warn_on_root = 1
