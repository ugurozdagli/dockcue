<p align="center">
  <img src="assets/hero.svg" alt="DockCue — ASTRO A50 X için mikrofon bildirimleri ve USB üzerinden medya kontrolü" width="100%">
</p>

<p align="center">
  <a href="https://github.com/ugurozdagli/dockcue/releases/latest"><img src="https://img.shields.io/github/v/release/ugurozdagli/dockcue?style=flat-square&amp;color=16848c&amp;label=release" alt="Son sürüm"></a>
  <a href="https://github.com/ugurozdagli/dockcue/actions/workflows/windows.yml"><img src="https://github.com/ugurozdagli/dockcue/actions/workflows/windows.yml/badge.svg" alt="Windows derlemesi"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-6f829c?style=flat-square" alt="MIT lisansı"></a>
  <img src="https://img.shields.io/badge/platform-Windows_x64-263c56?style=flat-square" alt="Windows x64">
</p>

<p align="center">
  <strong><a href="https://github.com/ugurozdagli/dockcue/releases/latest">Windows için indir</a></strong>
  &nbsp; · &nbsp; <a href="README.md">English</a>
  &nbsp; · &nbsp; <a href="#kurulum">Kurulum</a>
  &nbsp; · &nbsp; <a href="PRIVACY.md">Gizlilik</a>
  &nbsp; · &nbsp; <a href="https://github.com/ugurozdagli/dockcue/issues">Sorun bildir</a>
</p>

# A50 X için birkaç kullanışlı ek özellik

DockCue, **Logitech G ASTRO A50 X** için küçük bir Windows destek uygulamasıdır. Mikrofon kolunu açıp kapatırken farklı sesler duyun; mevcut USB bağlantınız üzerinden **Voice veya Game** tuşuyla medyayı oynatıp duraklatın. Pencereyi kapatın, uygulama sistem tepsisinde çalışmaya devam etsin.

> **Bağımsız topluluk uygulamasıdır.** Logitech’in resmî ürünü değildir; Logitech veya ASTRO ile ilişkili değildir. Yapay zekâ desteğiyle hazırlanmıştır. Ses kaydı, telemetri veya uzaktan erişim sunucusu yoktur.

## Neler sunuyor?

| Mikrofonu duyun | Medyayı kontrol edin | Sade kullanın |
| :--- | :--- | :--- |
| Açılma ve sessize alma için farklı sesler, ses seviyesi ayarı ve dinleme düğmesi. | Oynat / duraklat için **Voice** veya **Game** seçimi. Denge merkeze döner. | Kompakt pencere, sistem tepsisi, isteğe bağlı başlangıç ve Türkçe / İngilizce arayüz. |

## Arayüze göz atın

![DockCue 1.2.1 kompakt arayüzünün açıklamalı temsili görünümü](assets/interface-overview.svg)

*Güncel yerleşimin örnek değerlerle hazırlanmış temsili görünümüdür. Pil ve stant bilgisi bazın **son bildirimidir**; kulaklığın açık olduğunu kanıtlamaz.*

<details>
<summary>Gerçek uygulama ekran görüntüsü — önceki 1.2.0 arayüzü</summary>

Aşağıdaki görüntü önceki, daha büyük arayüze aittir. 1.2.1 sürümü yukarıda açıklanan kompakt yerleşimi kullanır.

<img src="assets/screenshot-en.png" alt="DockCue 1.2.0 gerçek İngilizce ayar penceresi" width="420">

</details>

## Kurulum

1. **[Son Windows x64 ZIP dosyasını indirin](https://github.com/ugurozdagli/dockcue/releases/latest)** ve kalıcı olarak kullanacağınız yazılabilir bir klasöre çıkartın.
2. **`DockCue.exe`** dosyasını çalıştırın. A50 X bazını PC’ye USB ile bağlayın.
3. Medya kontrolü için **Logitech G HUB** açık kalsın. Tarayıcıdaki videoyu bir kez oynatın.
4. DockCue’da **Voice** veya **Game** seçin; kulaklığın o tarafına kısa basın.
5. Başlangıç ve dil seçenekleri için **Ayarlar ve günlük** bölümünü açın. Pencereyi kapatmak uygulamayı tepsiye gizler; tamamen kapatmak için tepsi menüsünden **DockCue’dan çık** seçeneğini kullanın.

**Güncelleme:** Eski uygulamadan çıkıp dosyayı değiştirin. Ayarlarınızı korumak için `data/` klasörünü saklayın. Uygulama klasörünü taşırsanız **Windows ile başlat** ayarını güncelleyin.

Sürüm taşınabilir ve dijital olarak imzalanmamıştır. Doğrulama dosyası `SHA256SUMS.txt` sürüm sayfasındadır. Herkese açık ikili dosyalar GitHub Actions üzerinde derlenir.

## Mevcut kurulumunuzla çalışır

![A50 X tuşları mevcut USB bazından DockCue ve yerel G HUB’a, ardından Windows medya oturumuna ulaşır](assets/how-it-works.svg)

| Medya kontrolü açıkken | Medya kontrolü kapalıyken |
| :--- | :--- |
| Seçili Voice / Game yönü oynat / duraklat gönderir. İki yön de merkeze döner. | Game / Voice dengesi serbestçe ayarlanır. |
| **Oyun / sohbeti ortala** medya komutu göndermeden dengeyi sıfırlar. | G HUB bağlıyken ortalama düğmesi yine çalışır. |

Windows, klavyedeki medya tuşlarında olduğu gibi etkin medya oturumunu kullanır; başka bir medya uygulaması hedefi devralabilir. Bluetooth tuşu yeniden atanmaz. PC’de Bluetooth bulunması gerekmez.

## Yerel çalışır

- **Ses kaydı, hesap, telemetri, otomatik güncelleme veya bulut bağımlılığı yoktur.**
- Uygulama yalnızca yerel G HUB’a **`127.0.0.1:9010`** üzerinden istemci olarak bağlanır; TCP portu dinlemez.
- Ayarlar ve küçük dönen günlük dosyası uygulamanın **`data/`** klasöründe kalır.
- Günlükler ham USB raporu, seri numarası, aygıt yolu, erişim anahtarı, ses veya kişisel dosya yolu içermez.
- Çalışma ayarları, günlükler ve tanılama dosyaları kaynak koduna veya sürüm ZIP’ine eklenmez.

[Gizlilik ayrıntıları](PRIVACY.md) · [Güvenlik politikası](SECURITY.md)

## Uyumluluk ve bilinmesi gerekenler

| Konu | Durum |
| :--- | :--- |
| İşletim sistemi | Windows x64; canlı doğrulama Windows 11 üzerinde |
| Kulaklık | ASTRO A50 X, USB `046D:0B0B`, test edilen firmware `1.3.21` |
| G HUB | Medya kontrolü ve ortalama için gerekli; mikrofon sesleri için gerekli değil |
| Dil | Türkçe Windows’ta Türkçe, diğerlerinde İngilizce; elle değiştirilebilir |
| Diğer A50 nesilleri | Destek iddiası yok |

<details>
<summary>Bağlantı, denge ve bilinen sınırlamalar</summary>

- Kulaklık kapalıyken veya şarjdayken **bazın USB üzerinden bağlı kalması normaldir**. Pil değeri önbellekten gelebilir; yanıtlar kesilirse eski değer gizlenir.
- Mikrofon ve şarj standı durumu bazın son raporudur. Kulaklığın açık veya kablosuz bağlantısının etkin olduğunu kanıtlamaz.
- Standına koymak, kulaklığı kapatmak veya USB’yi ayırmak DockCue’yu kapatmamalıdır. Uygulama bağlantıyı yeniden dener.
- Medya modunda denge **12 üzerinden 6**, yani merkezde tutulur. Serbest ayar için medya kontrolünü kapatın.
- G HUB’da dengeyi seçili yöne sürüklemek de oynat / duraklat gönderebilir. Kulaklık tuşuna kısa basın.
- Başlangıç, elle ortalama ve gecikmiş geri yükleme bildirimlerinin ek medya komutu göndermesi engellenir.
- Test edilen kurulumda Bluetooth tuşu USB olayı üretmemiştir.
- Mikrofon sesleri varsayılan Windows ses çıkışını; medya komutları etkin Windows medya oturumunu kullanır.

</details>

<details>
<summary>Kaynak koddan derleme</summary>

Windows x64 ve Python 3.11+ gerekir.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python tools\build.py
```

ZIP, bağımlılık lisansları ve doğrulama dosyası `release/` klasörüne yazılır. Herkese açık ikili dosyalar geliştiricinin kişisel çalışma alanından değil, GitHub Actions üzerinden hazırlanır.

</details>

## DockCue’ya katkıda bulunun

Bir hata bulduysanız veya farklı firmware ile test ettiyseniz [issue açın](https://github.com/ugurozdagli/dockcue/issues). DockCue / Windows / firmware sürümlerini ve yeniden üretme adımlarını belirtin. Paylaşacağınız dosyaları gözden geçirin; aygıt kimlikleri veya kişisel dosyaları eklemeyin.

[Değişiklikler](CHANGELOG.md) · [Katkı rehberi](CONTRIBUTING.md) · [Üçüncü taraf bildirimleri](THIRD_PARTY_NOTICES.md) · [MIT Lisansı](LICENSE)
