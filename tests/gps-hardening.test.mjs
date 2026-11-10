import test from 'node:test';
import assert from 'node:assert/strict';
import {GpsEngineV03} from '../static/gps-v03.mjs';
const now=Date.parse('2026-11-09T12:00:00Z');
const point={timestamp:now,coords:{latitude:42.7,longitude:23.3,accuracy:5,speed:900}};
class Store{constructor(){this.points=[]}async list(prefix){return this.points.filter(p=>p.id.startsWith(prefix))}async put(p){this.points.push(p)}async remove(id){this.points=this.points.filter(p=>p.id!==id)}}
function engine(store,api){const e=new GpsEngineV03({store,api,actorId:'u',deviceId:'d',now:()=>now});e.running=true;return e}
test('GPS speed is capped to avoid implausible readings',async()=>{const s=new Store(),e=engine(s,async()=>{throw Error('offline')});await e.accept(point);await e.flush();assert.equal(s.points.length,1);assert.equal(s.points[0].payload.speed_mps,null)});
test('concurrent flush calls share a single operation',async()=>{const s=new Store();let calls=0;const e=engine(s,async()=>{calls++;await new Promise(r=>setTimeout(r,10));return {ok:true}});await s.put({id:e.prefix+'1',created:now,payload:{device_event_id:'one'}});await Promise.all([e.flush(),e.flush(),e.flush()]);assert.equal(calls,1);assert.equal(s.points.length,0)});
test('server error keeps point durable',async()=>{const s=new Store(),e=engine(s,async()=>{throw Error('server down')});await e.accept(point);await e.flush();assert.equal(s.points.length,1);assert.equal(e.state,'pending_sync')});
