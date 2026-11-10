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
