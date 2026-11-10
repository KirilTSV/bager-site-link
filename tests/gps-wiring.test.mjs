import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
test('HTML loads the GPS map JS and CSS',()=>{
 const html=read('templates/app.html');
 assert.match(html,/\/static\/field-command\.js/);
 assert.match(html,/\/static\/field-command\.css/);
 assert.match(html,/\/static\/app\.js/);
});
test('app uses durable GPS engine and shift restoration, not old localStorage flush',()=>{
 const app=read('static/app.js');
 assert.match(app,/import\('\/static\/gps-v03\.mjs'\)/);
 assert.match(app,/await restoreGpsShift\(\)/);
 assert.doesNotMatch(app,/function flushGpsQueue\(/);
});
test('field map only appears for field roles',()=>{
 const field=read('static/field-command.js');
 assert.match(field,/\['driver','operator'\]/);
 assert.match(field,/lastPosition/);
});

test('GPS UI has no legacy parallel queue or watch state',()=>{
 const app=read('static/app.js');
 for(const name of ['watchId','gpsTimer','lastGpsSentAt','gpsQueue'])assert.doesNotMatch(app,new RegExp('\\b'+name+'\\b'));
 assert.ok(app.includes('new GpsEngineV03({store,api,geo:navigator.geolocation,actorId,deviceId,onUpdate:gpsMessage,onPosition:'));
 assert.ok(app.includes('new IndexedGpsStore()'));
});
