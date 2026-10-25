"""English fallback and Turkish UI text."""
TEXT = {
"en": {
 "subtitle":"An independent A50 X companion", "alive":"Running", "base_yes":"Base connected by USB", "base_no":"Waiting for USB base",
 "mic_on":"Microphone open", "mic_off":"Microphone muted", "mic_wait":"Microphone status pending", "docked":"Docked / charging", "last_mic":"Last reported microphone state",
 "battery":"Battery", "battery_unknown":"Battery not available", "battery_note":"Reported by the base; may be cached when the headset is off.",
 "sounds":"Microphone cues", "sounds_sub":"Different sounds for open and mute", "preview":"Preview",
 "media":"Headset media control", "media_ready":"Play / pause · G HUB ready", "media_wait":"Waiting for G HUB", "media_off":"Original mix controls", "media_action":"Play / pause sent",
 "button":"Media button", "voice":"Voice", "game":"Game", "startup":"Start with Windows", "language":"Language", "system":"System default",
 "privacy":"Local only · no recording · no telemetry", "unofficial":"Not an official Logitech application.", "independent":"Not affiliated with Logitech or ASTRO.", "ai":"Created with AI assistance.",
 "hide":"Hide to tray", "open":"Open settings", "exit":"Quit DockCue", "logs":"View local log", "history":"Recent activity",
 "evt_start":"Application started", "evt_mic_on":"Microphone opened", "evt_mic_off":"Microphone muted", "evt_base_yes":"USB base connected", "evt_base_no":"USB base disconnected",
 "evt_ghub_yes":"G HUB connected", "evt_ghub_no":"G HUB unavailable; retrying", "evt_hidden":"Window hidden; still running", "evt_shown":"Settings window opened", "evt_exit":"Normal application exit", "evt_media":"Media command sent", "evt_error":"A recoverable error was logged", "evt_dock":"Headset docked / charging", "evt_undock":"Headset no longer docked",
 "uptime":"Uptime", "log_note":"Only local app events; no audio or device identifiers.", "startup_error":"Could not update Windows startup.", "error_title":"DockCue", "tray_error":"Tray unavailable; keeping the window open.",
},
"tr": {
 "subtitle":"Bağımsız A50 X destek uygulaması", "alive":"Çalışıyor", "base_yes":"Baz USB üzerinden bağlı", "base_no":"USB baz istasyonu bekleniyor",
 "mic_on":"Mikrofon açık", "mic_off":"Mikrofon kapalı", "mic_wait":"Mikrofon durumu bekleniyor", "docked":"Standında / şarj oluyor", "last_mic":"Son bildirilen mikrofon durumu",
 "battery":"Pil", "battery_unknown":"Pil bilgisi alınamadı", "battery_note":"Bazın bildirdiği değer; kulaklık kapalıyken önbellekten gelebilir.",
 "sounds":"Mikrofon bildirimleri", "sounds_sub":"Açılma ve kapanma için farklı sesler", "preview":"Dinle",
 "media":"Kulaklıktan medya kontrolü", "media_ready":"Oynat / duraklat · G HUB hazır", "media_wait":"G HUB bağlantısı bekleniyor", "media_off":"Normal oyun / sohbet dengesi", "media_action":"Oynat / duraklat gönderildi",
 "button":"Medya tuşu", "voice":"Voice", "game":"Game", "startup":"Windows ile başlat", "language":"Dil", "system":"Sistem varsayılanı",
 "privacy":"Yerel çalışır · ses kaydı ve telemetri yok", "unofficial":"Logitech’in resmî uygulaması değildir.", "independent":"Logitech veya ASTRO ile bağlantılı değildir.", "ai":"Yapay zekâ desteği ile hazırlanmıştır.",
 "hide":"Tepsiye gizle", "open":"Ayarları aç", "exit":"DockCue’dan çık", "logs":"Yerel logu aç", "history":"Son etkinlikler",
 "evt_start":"Uygulama başlatıldı", "evt_mic_on":"Mikrofon açıldı", "evt_mic_off":"Mikrofon kapatıldı", "evt_base_yes":"USB baz istasyonu bağlandı", "evt_base_no":"USB baz istasyonu ayrıldı",
 "evt_ghub_yes":"G HUB bağlantısı kuruldu", "evt_ghub_no":"G HUB bekleniyor; yeniden denenecek", "evt_hidden":"Pencere gizlendi; uygulama çalışıyor", "evt_shown":"Ayar penceresi açıldı", "evt_exit":"Uygulama normal olarak kapatıldı", "evt_media":"Medya komutu gönderildi", "evt_error":"Yerel loga bir hata kaydedildi", "evt_dock":"Kulaklık standında / şarj oluyor", "evt_undock":"Kulaklık standından ayrıldı",
 "uptime":"Çalışma süresi", "log_note":"Yalnızca yerel uygulama olayları; ses ve aygıt kimlikleri yok.", "startup_error":"Windows başlangıç ayarı değiştirilemedi.", "error_title":"DockCue", "tray_error":"Tepsi kullanılamadı; pencere açık tutuluyor.",
}}


def text(language, key):
    return TEXT.get(language, TEXT["en"]).get(key, TEXT["en"].get(key, key))
