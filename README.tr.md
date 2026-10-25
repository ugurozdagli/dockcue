# DockCue

Logitech G ASTRO A50 X için küçük, yerel çalışan Windows destek uygulaması.

[Windows sürümünü indir](https://github.com/ugurozdagli/dockcue/releases/latest) · [English](README.md)

- Mikrofonu kaldırınca ve indirince farklı bildirim sesleri.
- USB ses bağlantısını koruyarak **Voice veya Game** ile oynat/duraklat.
- Çarpı ve küçültme düğmeleriyle sistem tepsisinde çalışmaya devam etme.
- İsteğe bağlı Windows başlangıcı; doğrudan tepside açılır.
- Türkçe Windows'ta Türkçe, diğer Windows dillerinde İngilizce arayüz.
- Çalışma süresi, son etkinlikler ve küçük bir yerel log.

**Logitech’in resmî uygulaması değildir. Logitech veya ASTRO ile bağlantılı değildir.**
Bağımsız geliştirici destek uygulamasıdır; yapay zekâ desteği ile hazırlanmıştır.

## Kullanım

Release ZIP dosyasını kalıcı ve yazılabilir bir klasöre çıkarıp `DockCue.exe`
dosyasını aç. Baz istasyonunu USB ile bağla. Medya kontrolü için G HUB arka planda
açık kalsın. Tarayıcıdaki videoyu bir kez oynat, seçtiğin tuşa kısa bas.

Çarpı uygulamayı kapatmaz. Tamamen kapatmak için tepsi simgesine sağ tıkla ve
**DockCue’dan çık** seç. **Windows ile başlat** seçeneği başlangıç kaydını yönetir.
Ses düzeyi, dil ve tuş seçimi aynı klasörün `data/settings.json` dosyasında saklanır.

Bazın USB bağlantısı kulaklık kapalıyken veya şarjdayken devam eder; bu normaldir.
Pil bilgisi bazın önbelleğinden gelebilir. USB bağlantısı kulaklığın açık olduğunu
kanıtlamaz; mikrofon durumu son bildirilen bilgi olarak gösterilir.

Voice/Game seçimi, oyun/sohbet dengesindeki değişiklikten algılanır ve denge geri
alınır. Bu nedenle G HUB'dan aynı yönde denge değiştirmek de medya komutu
tetikleyebilir. Diğer taraf normal denge ayarını yapar. Özellik kapatılırsa iki
taraf da normal işlevinde çalışır. Bluetooth tuşu yeniden atanmaz.

Uygulama mikrofon sesi kaydetmez, telemetri göndermez ve uzaktan erişim sunmaz.
Yalnızca aynı bilgisayardaki G HUB'a `127.0.0.1:9010` üzerinden bağlanır; ağda
dinleyen bir sunucu açmaz. Loglar yereldir ve otomatik paylaşılmaz.

Kurulum, sınırlamalar ve derleme bilgileri için [İngilizce README](README.md).
