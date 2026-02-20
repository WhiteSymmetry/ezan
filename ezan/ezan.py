## `ezan/ezan.py`
"""
Ezan - Namaz vakitleri ve kıble hesaplama modülü.
"""

from astropy.coordinates import EarthLocation, AltAz, get_sun
from astropy.time import Time, TimeDelta
import astropy.units as u
import datetime
import pytz
import math
import requests

# ================== SABİTLER ==================
DEFAULT_LAT = 41.0082      # İstanbul
DEFAULT_LON = 28.9784
DEFAULT_TZ = 'Europe/Istanbul'

MECCA_COORDS = {'lat': 21.4225, 'lon': 39.8262}

# Diyanet referans açıları (derece)
ANGLES = {
    'imsak': -18.0,
    'isha': -17.0,
    'sun_alt': -0.833,      # güneş doğuş/batış
    'dhuhr_offset': 2.0      # öğle için zenit sonrası düşüş
}

# ================== YARDIMCI FONKSİYONLAR ==================
def get_user_location_and_date():
    """IP üzerinden konum ve bugünün tarihini alır, başarısız olursa varsayılanları döndürür."""
    try:
        today = datetime.date.today()
        print(f"✅ Sistem tarihi alındı: {today}")
    except Exception:
        today = datetime.date(2025, 12, 1)
        print(f"⚠️ Sistem tarihi alınamadı, varsayılan tarih kullanılıyor: {today}")

    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = data.get('lat', DEFAULT_LAT)
            lon = data.get('lon', DEFAULT_LON)
            tz = data.get('timezone', DEFAULT_TZ)
            city = data.get('city', 'İstanbul')
            country = data.get('country', 'Türkiye')
            print(f"✅ Konum bilgisi alındı: {city}, {country}")
            print(f"📍 Enlem: {lat}, Boylam: {lon}")
            return lat, lon, tz, today
    except Exception:
        print("⚠️ Otomatik konum alınamadı, varsayılan değerler kullanılıyor")

    return DEFAULT_LAT, DEFAULT_LON, DEFAULT_TZ, today


def get_manual_input():
    """Kullanıcıdan manuel olarak konum ve tarih bilgisi alır."""
    print("\n" + "=" * 50)
    print("MANUEL GİRİŞ")
    print("=" * 50)

    try:
        # Tarih
        date_str = input("Tarih (YYYY-AA-GG) [Bugün için boş bırakın]: ").strip()
        if date_str:
            year, month, day = map(int, date_str.split('-'))
            date = datetime.date(year, month, day)
        else:
            date = datetime.date.today()

        # Enlem
        lat_str = input(f"Enlem (derece) [Varsayılan: {DEFAULT_LAT}]: ").strip()
        latitude = float(lat_str) if lat_str else DEFAULT_LAT

        # Boylam
        lon_str = input(f"Boylam (derece) [Varsayılan: {DEFAULT_LON}]: ").strip()
        longitude = float(lon_str) if lon_str else DEFAULT_LON

        # Zaman dilimi
        tz_str = input(f"Zaman dilimi [Varsayılan: {DEFAULT_TZ}]: ").strip()
        timezone = tz_str if tz_str else DEFAULT_TZ
        if timezone not in pytz.all_timezones:
            print(f"⚠️ Geçersiz zaman dilimi '{timezone}', varsayılan kullanılıyor.")
            timezone = DEFAULT_TZ

        print(f"\n✅ Girilen değerler:")
        print(f"   Tarih: {date}")
        print(f"   Enlem: {latitude}")
        print(f"   Boylam: {longitude}")
        print(f"   Zaman Dilimi: {timezone}")

        return latitude, longitude, timezone, date

    except Exception as e:
        print(f"❌ Giriş hatası: {e}")
        print("Varsayılan değerler kullanılıyor...")
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_TZ, datetime.date.today()


def convert_astropy_to_datetime(astropy_time, timezone):
    """Astropy zaman nesnesini yerel datetime'a dönüştürür."""
    try:
        utc_time = astropy_time.to_datetime(timezone=pytz.UTC)
        local_tz = pytz.timezone(timezone)
        return utc_time.astimezone(local_tz)
    except (ValueError, AttributeError, pytz.UnknownTimeZoneError) as e:
        print(f"⚠️ Zaman dönüşüm hatası: {e}, naive datetime döndürülüyor.")
        return astropy_time.to_datetime()


def binary_search_altitude(location, obs_time_start, left_sec, right_sec,
                            target_altitude, is_rising=True, tolerance=1, max_iter=50):
    """
    Belirtilen zaman aralığında hedef güneş yüksekliğine ulaşılan anı binary search ile bulur.
    is_rising=True: yükselirken hedef yüksekliğe ulaşma (alçalan için is_rising=False).
    Geriye saniye cinsinden süre döndürür (obs_time_start'tan itibaren).
    """
    left, right = left_sec, right_sec
    for _ in range(max_iter):
        if right - left <= tolerance:
            break
        mid = (left + right) / 2
        t = obs_time_start + TimeDelta(mid, format='sec')
        alt = get_sun(t).transform_to(AltAz(obstime=t, location=location)).alt.degree

        if is_rising:
            # yükselirken: hedefin altında -> ilerle, üstünde -> gerile
            if alt < target_altitude:
                left = mid
            else:
                right = mid
        else:
            # alçalırken: hedefin üstünde -> ilerle, altında -> gerile
            if alt > target_altitude:
                left = mid
            else:
                right = mid
    return (left + right) / 2


# ================== GÜNEŞ OLAYLARI ==================
def calculate_sun_event(latitude, longitude, date, timezone,
                        event_type='sunrise', target_alt=None, rising=None):
    """
    Güneş doğuşu, batışı veya belirli bir yüksekliğe ulaştığı anı hesaplar.
    event_type: 'sunrise', 'sunset', veya 'custom'
    target_alt: custom tipinde kullanılacak hedef yükseklik (derece)
    """
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    utc_start = datetime.datetime(date.year, date.month, date.day, tzinfo=pytz.UTC)
    obs_start = Time(utc_start, location=location)

    # Varsayılan aralıklar ve hedef yükseklik
    if event_type == 'sunrise':
        left, right = 4 * 3600, 10 * 3600
        target = ANGLES['sun_alt']
        rising = True
    elif event_type == 'sunset':
        left, right = 12 * 3600, 20 * 3600
        target = ANGLES['sun_alt']
        rising = False
    elif event_type == 'custom':
       left, right = 0, 24 * 3600
       target = target_alt
       # rising parametresi dışarıdan gelmeli
    else:  # custom
        left, right = 0, 24 * 3600
        target = target_alt
        rising = None  # dışarıdan belirtilmeli

    sec = binary_search_altitude(location, obs_start, left, right,
                                 target, rising, tolerance=1, max_iter=50)
    best_time = obs_start + TimeDelta(sec, format='sec')
    return convert_astropy_to_datetime(best_time, timezone)


def calculate_astronomical_twilight(latitude, longitude, date, timezone,
                                    is_morning=True, angle=-18.0):
    """Astronomik şafak (sabah veya akşam) hesabı."""
    return calculate_sun_event(latitude, longitude, date, timezone,
                               event_type='custom', target_alt=angle,
                               rising=is_morning)   # sabah True, akşam False

def calculate_solar_noon(latitude, longitude, date, timezone):
    """Güneşin tam tepede olduğu an."""
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    utc_start = datetime.datetime(date.year, date.month, date.day, tzinfo=pytz.UTC)
    obs_start = Time(utc_start, location=location)

    left, right = 9 * 3600, 15 * 3600
    tolerance = 1
    for _ in range(50):
        if right - left <= tolerance:
            break
        mid = (left + right) / 2
        t_mid = obs_start + TimeDelta(mid, format='sec')
        t_right = obs_start + TimeDelta(right, format='sec')
        alt_mid = get_sun(t_mid).transform_to(AltAz(obstime=t_mid, location=location)).alt.degree
        alt_right = get_sun(t_right).transform_to(AltAz(obstime=t_right, location=location)).alt.degree
        if alt_mid < alt_right:
            left = mid
        else:
            right = mid
    best_time = obs_start + TimeDelta((left + right) / 2, format='sec')
    return convert_astropy_to_datetime(best_time, timezone)


def calculate_dhuhr_time(latitude, longitude, date, timezone):
    """
    Hanefi'ye göre öğle namazı vakti: güneşin tam tepeden 2° aşağı indiği an.
    """
    noon_time = calculate_solar_noon(latitude, longitude, date, timezone)
    noon_utc = noon_time.astimezone(pytz.UTC)
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    obs_noon = Time(noon_utc, location=location)

    # Zenitteki yükseklik
    max_alt = get_sun(obs_noon).transform_to(AltAz(obstime=obs_noon, location=location)).alt.degree
    target_alt = max_alt - ANGLES['dhuhr_offset']

    # Arama aralığı: zenit öncesi 5 dk, sonrası 15 dk (±20 dk)
    left, right = -300, 900
    sec = binary_search_altitude(location, obs_noon, left, right,
                                 target_alt, is_rising=False, tolerance=0.1, max_iter=60)
    best_time = obs_noon + TimeDelta(sec, format='sec')
    return convert_astropy_to_datetime(best_time, timezone)


def calculate_shadow_altitude(shadow_ratio, latitude, date):
    """
    Verilen gölge oranı (1 veya 2) için gerekli güneş yüksekliğini hesaplar.
    Deklinasyon astropy'den alınır.
    """
    utc_noon = datetime.datetime(date.year, date.month, date.day, 12, 0, 0, tzinfo=pytz.UTC)
    time_noon = Time(utc_noon)
    sun = get_sun(time_noon)
    declination = sun.dec.degree

    delta = abs(latitude - declination)
    delta_rad = math.radians(delta)
    cot_alpha = shadow_ratio + math.tan(delta_rad)
    alpha_rad = math.atan(1.0 / cot_alpha)
    return math.degrees(alpha_rad)


def calculate_asr_time(latitude, longitude, date, timezone, shadow_ratio=1):
    """İkindi namazı vakti (standart veya Hanefi)."""
    noon_time = calculate_solar_noon(latitude, longitude, date, timezone)
    noon_utc = noon_time.astimezone(pytz.UTC)
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    obs_noon = Time(noon_utc, location=location)

    target_alt = calculate_shadow_altitude(shadow_ratio, latitude, date)

    # Arama aralığı: öğleden sonra
    if shadow_ratio == 1:
        left, right = 45 * 60, 180 * 60
    else:
        left, right = 90 * 60, 240 * 60

    sec = binary_search_altitude(location, obs_noon, left, right,
                                 target_alt, is_rising=False, tolerance=1, max_iter=50)
    best_time = obs_noon + TimeDelta(sec, format='sec')
    local_time = convert_astropy_to_datetime(best_time, timezone)

    # Standart ikindiye 15 dakika ekle (Diyanet uyumu için)
    if shadow_ratio == 1:
        local_time += datetime.timedelta(minutes=15)
    return local_time


# ================== KIBLE FONKSİYONLARI ==================
def qibla_angle(lat, lon):
    """Kuzeyden saat yönünde kıble açısını hesaplar (0-360)."""
    delta_lon = math.radians(MECCA_COORDS['lon'] - lon)
    lat1 = math.radians(lat)
    lat2 = math.radians(MECCA_COORDS['lat'])
    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360


def calculate_qibla_time(lat, lon, date, tz):
    """
    Güneşin azimutunun kıble açısına eşit olduğu anı bulur.
    Güneş doğuşu ile batışı arasında arama yapar.
    """
    try:
        sunrise = calculate_sun_event(lat, lon, date, tz, 'sunrise')
        sunset = calculate_sun_event(lat, lon, date, tz, 'sunset')
    except Exception as e:
        print(f"⚠️ Güneş doğuş/batış hesaplanamadı: {e}")
        return []

    utc_date = datetime.datetime(date.year, date.month, date.day, tzinfo=pytz.UTC)
    sunrise_utc = sunrise.astimezone(pytz.UTC)
    sunset_utc = sunset.astimezone(pytz.UTC)

    start_sec = (sunrise_utc - utc_date).total_seconds()
    end_sec = (sunset_utc - utc_date).total_seconds()

    target_az = qibla_angle(lat, lon)
    location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg)

    t_start = Time(utc_date) + TimeDelta(start_sec, format='sec')
    t_end = Time(utc_date) + TimeDelta(end_sec, format='sec')
    az_start = get_sun(t_start).transform_to(AltAz(obstime=t_start, location=location)).az.degree
    az_end = get_sun(t_end).transform_to(AltAz(obstime=t_end, location=location)).az.degree

    # Azimut sürekli artar; hedef bu aralıkta mı?
    if az_start <= target_az <= az_end:
        left, right = start_sec, end_sec
        for _ in range(50):
            if right - left <= 1:
                break
            mid = (left + right) / 2
            t_mid = Time(utc_date) + TimeDelta(mid, format='sec')
            az_mid = get_sun(t_mid).transform_to(AltAz(obstime=t_mid, location=location)).az.degree
            if az_mid < target_az:
                left = mid
            else:
                right = mid
        best_sec = (left + right) / 2
        best_utc = Time(utc_date) + TimeDelta(best_sec, format='sec')
        local_time = convert_astropy_to_datetime(best_utc, tz)
        return [local_time]
    else:
        return []


# ================== ÇIKTI FONKSİYONU ==================
def print_prayer_times(latitude, longitude, timezone, date):
    """Tüm namaz vakitlerini ve kıble bilgilerini yazdırır."""
    print("\n" + "=" * 70)
    print(f"🌙 NAMAZ VAKİTLERİ - {date}")
    print(f"📍 Konum: Enlem {latitude:.4f}, Boylam {longitude:.4f}")
    print(f"🕒 Zaman Dilimi: {timezone}")
    print("=" * 70)

    try:
        # Vakit hesaplamaları
        imsak = calculate_astronomical_twilight(latitude, longitude, date, timezone,
                                                is_morning=True, angle=ANGLES['imsak'])
        sunrise = calculate_sun_event(latitude, longitude, date, timezone, 'sunrise')
        solar_noon = calculate_solar_noon(latitude, longitude, date, timezone)
        dhuhr = calculate_dhuhr_time(latitude, longitude, date, timezone)
        asr_std = calculate_asr_time(latitude, longitude, date, timezone, 1)
        asr_han = calculate_asr_time(latitude, longitude, date, timezone, 2)
        maghrib = calculate_sun_event(latitude, longitude, date, timezone, 'sunset')
        isha = calculate_astronomical_twilight(latitude, longitude, date, timezone,
                                               is_morning=False, angle=ANGLES['isha'])

        vakitler = [
            ("🌅 İmsak/Fecr/Fajr(فجر)", imsak,
             f"Astronomik şafak ({ANGLES['imsak']}°) – Diyânet imsak vakti?\nNot: Tam -18° aslında 0° ekvator enlemi için geçerlidir"),
            ("☀️ Güneşin Doğuşu/Sunrise(شروق)", sunrise,
             f"Güneş ufuk çizgisinde ({ANGLES['sun_alt']}°)"),
            ("🌞 Öğle Namazı/Dhuhr/Zhuhr(ظهر)", dhuhr,
             f"Güneş zenitten {ANGLES['dhuhr_offset']}° aşağıda (Hanefi)"),
            ("🌇 İkindi - Standart/Asr(عصر)", asr_std,
             "Gölge boyu = 1 cisim boyu"),
            ("🌆 İkindi - Hanefi/Asr(عصر)", asr_han,
             "Gölge boyu = 2 cisim boyu"),
            ("🌄 Akşam Namazı/Maghrib(مغرب)", maghrib,
             f"Güneş batışı ({ANGLES['sun_alt']}°)"),
            ("🌙 Yatsı Namazı/Isha(عشاء)", isha,
             f"Diyanet yatsı vakti ({ANGLES['isha']}°)\nAstronomik şafak ise {ANGLES['imsak']}°")
        ]

        for isim, vakit, aciklama in vakitler:
            print(f"{isim:.<25} {vakit.strftime('%H:%M:%S')}")
            print(f"   {aciklama}")

        # Astronomik bilgiler (astropy'den deklinasyon)
        utc_noon = datetime.datetime(date.year, date.month, date.day, 12, 0, 0, tzinfo=pytz.UTC)
        sun = get_sun(Time(utc_noon))
        declination = sun.dec.degree
        print("\n📊 ASTRONOMİK BİLGİLER")
        print(f"   Güneş Deklinasyonu: {declination:.2f}°")
        print(f"   Yılın Günü: {date.timetuple().tm_yday}")
        print(f"   Güneş Tepe Noktası: {solar_noon.strftime('%H:%M:%S')}")

        # Kıble
        print("\n🕋 KIBLE BİLGİLERİ")
        kible_aci = qibla_angle(latitude, longitude)
        print(f"   Kıble Açısı (Kuzeyden saat yönünde): {kible_aci:.2f}°")
        kible_saatleri = calculate_qibla_time(latitude, longitude, date, timezone)
        if kible_saatleri:
            for i, t in enumerate(kible_saatleri):
                print(f"   Kıble Saati {i+1}: {t.strftime('%H:%M:%S')} (Güneş tam kıble yönünde)")
        else:
            print("   Bugün için kıble saati bulunamadı (güneş doğuşu ile batışı arasında)")

    except Exception as e:
        print(f"❌ Hesaplama hatası: {e}")
        print("Lütfen farklı değerler deneyin.")

    print("=" * 70)


# ================== ANA PROGRAM ==================
def main():
    print("🌙🕌 Kod İle Namaz/Salât Vakitleri Hesaplayıcısı")
    print("Not: Kod ile hesaplandığından yerel takvimlerden küçük sapmalar olabilir.")
    print("=" * 50)

    while True:
        print("\nSeçenekler:")
        print("1 - Otomatik konum ve bugünün tarihi")
        print("2 - Farklı giriş seçenekleri (manuel)")
        print("3 - Çıkış")

        secim = input("\nSeçiminiz (1-3): ").strip()
        if secim not in ('1', '2', '3'):
            print("❌ Geçersiz seçim! Lütfen 1, 2 veya 3 girin.")
            continue

        if secim == '3':
            print("👋 Allāh (c.c)'ne emânet olunuz (May Allah (swt) protect you!)!")
            print("👋 في أمان الله (سبحانه وتعالى)!")
            print("👋 Fī amānillāh subḥānahu wa ta'ālā!")
            print("👋 Maşâllāh (Maşâe Allāh)!")
            break

        try:
            if secim == '1':
                lat, lon, tz, date = get_user_location_and_date()
            else:
                lat, lon, tz, date = get_manual_input()
            print_prayer_times(lat, lon, tz, date)
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {e}")
            print("Varsayılan değerlerle devam ediliyor...")
            print_prayer_times(DEFAULT_LAT, DEFAULT_LON, DEFAULT_TZ, datetime.date.today())


if __name__ == "__main__":
    main()
