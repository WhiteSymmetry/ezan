# Ezan

---

Ezan - Namaz vakitleri ve kıble hesaplama modülü.


Kullanım: Usage
---

from ezan import print_prayer_times, get_user_location_and_date

lat, lon, tz, date = get_user_location_and_date()
print_prayer_times(lat, lon, tz, date)

