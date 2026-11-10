import test from 'node:test';
import assert from 'node:assert/strict';
import {GpsEngineV03} from '../static/gps-v03.mjs';
test('GPS event ID fits PostgreSQL VARCHAR(80)',async()=>{
 const points=[];
 const store={list:async()=>points,put:async x=>{points.push(x)},remove:async()=>{}};
 const engine=new GpsEngineV03({store,api:async()=>({ok:false}),geo:null,actorId:'a'.repeat(36),deviceId:'d'.repeat(36),now:()=>1731234567890});
 engine.running=true;
 const ok=await engine.accept({timestamp:1731234567890,coords:{latitude:42.7,longitude:23.3,accuracy:6}});
 assert.equal(ok,true);assert.equal(points.length,1);
 assert.ok(points[0].payload.device_event_id.length<=80);
 assert.ok(points[0].id.length>80);
});
