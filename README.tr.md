# DockCue

Logitech G ASTRO A50 X için bağımsız, yerel çalışan Windows destek uygulaması.
Logitech veya ASTRO ile ilişkili değildir. Yapay zekâ desteğiyle hazırlanmıştır.

[Windows sürümünü indir](https://github.com/ugurozdagli/dockcue/releases/latest) · [English](README.md)

- Mikrofon kolu açılırken ve kapatılırken farklı sesler.
- USB bağlantısıyla Voice veya Game üzerinden oynat / duraklat.
- Medya kontrolü açıkken oyun / sohbet dengesi merkezde tutulur. Diğer yöne basmak medya komutu göndermez.
- **Oyun / sohbeti ortala** düğmesi dengeyi merkeze alır; oynat / duraklat göndermez.
- Dengeyi serbestçe ayarlamak için medya kontrolünü kapatın.
- Kompakt 420 × 510 arayüz. Başlangıç, dil ve son etkinlikler **Ayarlar ve günlük** altında.
- Pil yüzdesiyle birlikte bazın son bildirdiği şarj standı durumu gösterilir.
- Çarpı veya küçültme uygulamayı tepsiye gizler; çıkmak için tepsi menüsünden çıkışı seçin.
- İsteğe bağlı Windows başlangıcı, otomatik Türkçe / İngilizce ve yerel günlük.

ZIP dosyasını yazılabilir bir klasöre çıkartıp `DockCue.exe` dosyasını açın. Medya kontrolü için G HUB açık olmalıdır.
Tarayıcıda videoyu bir kez oynattıktan sonra seçtiğiniz tuşa kısa basın. Windows'un etkin medya oturumu kullanılır.
G HUB'da dengeyi seçili yöne sürüklemek de medya komutu gönderebilir.

Kulaklık kapalıyken veya şarjdayken bazın USB üzerinden bağlı görünmesi normaldir.
Pil, stant ve mikrofon bilgileri bazın son raporudur; kulaklığın açık olduğunu kanıtlamaz.

Ses kaydı, telemetri, bulut hesabı veya uzaktan erişim sunucusu yoktur. Tek ağ bağlantısı yerel G HUB'a
`127.0.0.1:9010` üzerinden istemci bağlantısıdır. Ayarlar ve sınırlı günlük `data/` klasöründe yerel kalır;
yayımlanan kaynak koduna veya ZIP'e eklenmez. [Gizlilik ayrıntıları](PRIVACY.md).

Windows 11 ve A50 X firmware 1.3.21 ile doğrulanmıştır. Diğer A50 nesilleri için destek iddiası yoktur.
Topluluk sürümü dijital olarak imzalanmamıştır; ZIP için `SHA256SUMS.txt` yayımlanır.

Kaynak derleme, bilinen sınırlamalar ve katkı bilgileri için [İngilizce README](README.md) dosyasına bakın.
