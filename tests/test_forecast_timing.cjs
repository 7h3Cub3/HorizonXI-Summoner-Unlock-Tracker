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
const MAX_WIKI_FUTURE_OFFSET=14;
const VISIBLE_UPCOMING_DAYS=7;
const VANA_DAYS=[];
const VANA_EPOCH_MS=0;
let wikiDayTimes={};
let wikiTimeCalibrationNote='';
const document={getElementById:()=>({textContent:''})};
function pad2(n){return String(n).padStart(2,'0')}
function fmtDuration(n){return String(n)}
`;
const verify = `
const now = new Date(2026, 9, 8, 11, 22, 0).getTime();
const day0 = new Date(2026, 9, 8, 11, 14, 0).getTime();
const day1 = new Date(2026, 9, 8, 12, 12, 0).getTime();
assert.equal(parseWikiEarthTimeLocal('08-Oct 11:14 AM', now, 0), day0);
assert.equal(parseWikiEarthTimeLocal('08-Oct 12:12 PM', now, 1), day1);
assert.equal(parseWikiEarthTimeLocal('2026-10-08 11:14',now,0), day0);
assert.equal(parseWikiEarthTimeLocal('bad data',now,0).toString(),'NaN');
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
assert.equal(futureDayTimeLabel(1),'08-Oct 12:12 PM');
assert.equal(nextWikiForecastRowMs(now),day1);
assert.ok(Number.isNaN(futureDayStartMs(7)));
const dec = new Date(2026,11,31,23,0).getTime();
assert.equal(parseWikiEarthTimeLocal('01-Jan 12:12 AM', dec,1),new Date(2027,0,1,0,12).getTime());
// Regression: raw Wiki +1 at 10:12 while it is 11:34 now must NOT render as future.
const observedNow = new Date(2026,9,8,11,34,3).getTime();
const oneVanaDay = 3456000;
const sourceDay1 = new Date(2026,9,8,10,12,0).getTime();
const rows={};
for(let offset=0;offset<=14;offset++){
  rows[offset]={offset,ts:sourceDay1+(offset-1)*oneVanaDay,raw:'wiki row',zone:'Buburimu Peninsula'};
}
wikiDayTimes=rows;
const upcoming=getUpcomingWikiRows(observedNow);
assert.equal(JSON.stringify(Array.from(upcoming,x=>x.offset)),'[3,4,5,6,7,8,9]');
assert.ok(upcoming.every(x=>x.ts>observedNow));
assert.equal(upcoming.length,7);
assert.equal(getUpcomingWikiRows(sourceDay1+oneVanaDay*12).length,1);

`;
const ctx={assert, Date, Number, String, Object, Array, Math, console};
vm.createContext(ctx);
vm.runInContext(prep+impl+verify,ctx,{filename:'tracker-time-test.js'});
console.log('PASS: Wiki offset 0 matches 08-Oct 11:14 AM; offset 1 matches 12:12 PM; no double offset.');
console.log('PASS: Yearless timestamps, ISO timestamps, year rollover, upcoming-row timer.');
console.log('PASS: Past source Day +1 and +2 hidden; next seven upcoming source days selected by Earth timestamp.');
