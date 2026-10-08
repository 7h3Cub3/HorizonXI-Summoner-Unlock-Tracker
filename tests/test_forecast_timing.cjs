'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'src', 'Carbuncle_Rainbow_Tracker.html'), 'utf8');
const start = html.indexOf('const WIKI_MONTHS=');
const end = html.indexOf('function renderFutureForecasts(forecasts){', start);
assert.ok(start > 0 && end > start, 'Wiki time parsing block must exist');
const impl = html.slice(start, end);

const prep = `
const VANA_DAY_MS=3456000;
const MAX_WIKI_FUTURE_OFFSET=36;
const FUTURE_DAY_CHOICES=[7,14,21,28];
const VISIBLE_UPCOMING_DAYS=7;
const VANA_DAYS=[];
const VANA_EPOCH_MS=0;
let wikiDayTimes={};
let settings={futureDays:7};
function selectedFutureDays(){const n=Number(settings.futureDays);return FUTURE_DAY_CHOICES.includes(n)?n:VISIBLE_UPCOMING_DAYS;}
let wikiTimeCalibrationNote='';
const document={getElementById:()=>({textContent:''})};
function pad2(n){return String(n).padStart(2,'0')}
function fmtDuration(n){return String(n)}
`;
const verify = `
const now = Date.UTC(2026, 9, 8, 11, 22, 0);
const day0 = Date.UTC(2026, 9, 8, 11, 14, 0);
const day1 = Date.UTC(2026, 9, 8, 12, 12, 0);
assert.equal(parseWikiEarthTimeUTC('08-Oct 11:14 AM', now, 0), day0);
assert.equal(parseWikiEarthTimeUTC('08-Oct 12:12 PM', now, 1), day1);
assert.equal(parseWikiEarthTimeUTC('2026-10-08 11:14',now,0), day0);
assert.equal(parseWikiEarthTimeUTC('bad data',now,0).toString(),'NaN');
setWikiForecastRowTimes({
  'Buburimu Peninsula':{
    earth_time:'08-Oct 11:14 AM',
    future:[
      {offset:1,earth_time:'08-Oct 12:12 PM'},
      {offset:2,earth_time:'08-Oct 01:09 PM'}
    ]
  }
},now);
assert.equal(wikiDayTimes[0].raw,'08-Oct 11:14 AM');
assert.equal(wikiDayTimes[1].raw,'08-Oct 12:12 PM');
assert.equal(futureDayStartMs(1),day1);
assert.equal(futureDayTimeLabel(1),localWikiEarthTime(day1));
assert.equal(nextWikiForecastRowMs(now),day1);
assert.ok(Number.isNaN(futureDayStartMs(7)));
// UTC 15:00 becomes 17:00 CEST on Oct 8, 2026; after DST ends, 16:00 CET.
const madridHour=(t)=>new Intl.DateTimeFormat('en-GB',{
  timeZone:'Europe/Madrid',hour:'2-digit',hourCycle:'h23'
}).format(new Date(t));
assert.equal(madridHour(Date.UTC(2026,9,8,15)), '17');
assert.equal(madridHour(Date.UTC(2026,9,28,15)), '16');
assert.equal(parseWikiEarthTimeUTC('08-Oct 03:00 PM',now,0),Date.UTC(2026,9,8,15));
// Absolute timestamp supplied by the Python helper must win over its display string.
setWikiForecastRowTimes({'Buburimu Peninsula':{
  earth_time:'08-Oct 03:00 PM',earth_unix_ms:Date.UTC(2026,9,8,15),future:[]
}}, Date.UTC(2026,9,8,15,10));
assert.equal(wikiDayTimes[0].ts,Date.UTC(2026,9,8,15));
// Regression: the same absolute UTC timestamp must display in a chosen IANA
// timezone even if the browser / GitHub runner itself uses UTC.
const fifteenUtc=Date.UTC(2026,9,8,15,0);
settings.displayTimeZone='Europe/Madrid';
assert.equal(selectedDisplayTimeZone(),'Europe/Madrid');
const madridDisplay=localWikiEarthTime(fifteenUtc);
assert.equal(madridDisplay,new Intl.DateTimeFormat(undefined,{
  day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',
  timeZoneName:'short',timeZone:'Europe/Madrid'
}).format(new Date(fifteenUtc)));
const madridParts=new Intl.DateTimeFormat('en-GB',{
  timeZone:selectedDisplayTimeZone(),hour:'2-digit',hourCycle:'h23'
}).format(new Date(fifteenUtc));
assert.equal(madridParts,'17');
const winterHour=new Intl.DateTimeFormat('en-GB',{
  timeZone:selectedDisplayTimeZone(),hour:'2-digit',hourCycle:'h23'
}).format(new Date(Date.UTC(2026,9,28,15)));
assert.equal(winterHour,'16');
settings.displayTimeZone='UTC';
assert.equal(selectedDisplayTimeZone(),'UTC');
assert.notEqual(localWikiEarthTime(fifteenUtc),madridDisplay);
settings.displayTimeZone='auto';
assert.equal(selectedDisplayTimeZone(),undefined);
const dec = Date.UTC(2026,11,31,23,0);
assert.equal(parseWikiEarthTimeUTC('01-Jan 12:12 AM', dec,1),Date.UTC(2027,0,1,0,12));
// Regression: raw Wiki +1 at 10:12 while it is 11:34 now must NOT render as future.
const observedNow = Date.UTC(2026,9,8,11,34,3);
const oneVanaDay = 3456000;
const sourceDay1 = Date.UTC(2026,9,8,10,12,0);
const rows={};
for(let offset=0;offset<=36;offset++){
  rows[offset]={offset,ts:sourceDay1+(offset-1)*oneVanaDay,raw:'wiki row',zone:'Buburimu Peninsula'};
}
wikiDayTimes=rows;
const upcoming=getUpcomingWikiRows(observedNow);
assert.equal(JSON.stringify(Array.from(upcoming,x=>x.offset)),'[3,4,5,6,7,8,9]');
assert.ok(upcoming.every(x=>x.ts>observedNow));
assert.equal(upcoming.length,7);
// The 7/14/21/28 selector controls the number of real upcoming rows.
settings.futureDays=7;
assert.equal(getUpcomingWikiRows(observedNow).length,7);
settings.futureDays=14;
assert.equal(getUpcomingWikiRows(observedNow).length,14);
settings.futureDays=21;
assert.equal(getUpcomingWikiRows(observedNow).length,21);
settings.futureDays=28;
const longRange=getUpcomingWikiRows(observedNow);
assert.equal(longRange.length,28);
assert.equal(longRange[0].offset,3);
assert.equal(longRange[27].offset,30);
assert.ok(longRange.every(x=>x.ts>observedNow));
// With fewer Wiki source rows, show only authentic rows, never extrapolate.
wikiDayTimes=Object.fromEntries(Object.entries(rows).filter(([k])=>+k<=14));
assert.equal(getUpcomingWikiRows(observedNow).length,12);
// Bad stored values fall back to the default rather than a nonsense horizon.
settings.futureDays=999;
assert.equal(selectedFutureDays(),7);
settings.futureDays='14';
assert.equal(selectedFutureDays(),14);

`;
const ctx={assert, Date, Number, String, Object, Array, Math, Intl, console};
vm.createContext(ctx);
vm.runInContext(prep+impl+verify,ctx,{filename:'tracker-time-test.js'});
console.log('PASS: Wiki UTC offset 0 matches 08-Oct 11:14 AM and offset 1 matches 12:12 PM UTC.');
console.log('PASS: explicit display timezone Europe/Madrid converts UTC 15:00 to 17:00 CEST and 16:00 CET; Browser automatic remains selectable.');
console.log('PASS: UTC timestamp precedence, ISO dates, year rollover.');
console.log('PASS: Past source Day +1 and +2 hidden; next seven upcoming source days selected by Earth timestamp.');
console.log('PASS: Future-day choices 7/14/21/28; 28 real future rows selected when Wiki supplies them.');
console.log('PASS: Wiki-limited responses show fewer genuine rows; invalid saved values use 7.');
