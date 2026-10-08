import datetime as dt
import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/"src"/"weather_server.py"
spec=importlib.util.spec_from_file_location("hxi_weather_utc",PATH)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class WeatherUtcTests(unittest.TestCase):
    def test_wiki_unzoned_time_is_utc(self):
        now=dt.datetime(2026,10,8,15,30,tzinfo=dt.timezone.utc)
        self.assertEqual(m.wiki_utc_unix_ms("08-Oct 03:00 PM",0,now),1791471600000)
        self.assertEqual(m.wiki_utc_unix_ms("2026-10-08 15:00",0,now),1791471600000)
        self.assertEqual(m.wiki_utc_unix_ms("2026-10-08T15:00:00Z",0,now),1791471600000)
    def test_invalid_and_year_rollover(self):
        now=dt.datetime(2026,12,31,23,tzinfo=dt.timezone.utc)
        self.assertEqual(m.wiki_utc_unix_ms("01-Jan 12:12 AM",1,now),1798762320000)
        self.assertIsNone(m.wiki_utc_unix_ms("invalid",0,now))
    def test_forecast_fields(self):
        html='<table><tr><td>Buburimu_Peninsula</td><td>0</td><td>08-Oct 03:00 PM</td><td>Firesday</td><td>Moon</td><td>Clouds</td><td>Thunder</td><td>Thunderstorms</td></tr><tr><td>Buburimu_Peninsula</td><td>1</td><td>08-Oct 03:57 PM</td><td>Earthsday</td><td>Moon</td><td>Clouds</td><td>Thunder</td><td>Thunderstorms</td></tr></table>'
        rows,_=m.parse_forecast_days(html,'Buburimu_Peninsula')
        self.assertEqual(rows[1]['earth_unix_ms']-rows[0]['earth_unix_ms'],57*60000)

if __name__=='__main__':
    unittest.main()
