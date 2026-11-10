import test from 'node:test';import assert from 'node:assert/strict';import {GpsEngineV03} from '../static/gps-v03.mjs';
const time=Date.parse('2026-11-09T12:00:00Z');
class Store{constructor(){this.m=new Map();this.fail=false}async list(prefix){return [...this.m.values()].filter(p=>p.id.startsWith(prefix)).sort((a,b)=>a.created-b.created)}async put(p){if(this.fail)throw Error('disk full');this.m.set(p.id,p)}async remove(id){if(this.fail)throw Error('disk full');this.m.delete(id)}}
const pos=(t=time)=>({timestamp:t,coords:{latitude:42.7,longitude:23.3,accuracy:8,speed:0,heading:0}});
const setup=(store=new Store(),api=async()=>({ok:true}))=>{const e=new GpsEngineV03({store,api,actorId:'user',deviceId:'phone',now:()=>time});e.running=true;return {e,store}};
test('durable point saved before upload',async()=>{const s=new Store();const {e}=setup(s,async()=>{assert.equal(s.m.size,1);return {ok:true}});await e.accept(pos());await e.flush();assert.equal(s.m.size,0)});
test('offline point survives engine recreation',async()=>{const s=new Store();const {e}=setup(s,async()=>{throw Error('offline')});await e.accept(pos());await e.flush();assert.equal(s.m.size,1);const next=setup(s).e;await next.flush();assert.equal(s.m.size,0)});
test('unacknowledged response retains point',async()=>{const {e,store}=setup(new Store(),async()=>({ok:false}));await e.accept(pos());await e.flush();assert.equal(store.m.size,1)});
test('storage failure never claims success',async()=>{const s=new Store();s.fail=true;const {e}=setup(s);assert.equal(await e.accept(pos()),false);assert.equal(e.state,'storage_error')});
test('invalid coordinates rejected',async()=>{const {e,store}=setup();const p=pos();p.coords.latitude=120;assert.equal(await e.accept(p),false);assert.equal(store.m.size,0)});
test('sampling interval enforced',async()=>{const {e,store}=setup(new Store(),async()=>{throw Error('offline')});await e.accept(pos());await e.accept(pos(time+1000));await e.flush();assert.equal(store.m.size,1)});
test('separate participant/device queues',async()=>{const s=new Store();const a=setup(s,async()=>{throw Error('offline')}).e;await a.accept(pos());await a.flush();const b=new GpsEngineV03({store:s,api:async()=>({ok:true}),actorId:'other',deviceId:'phone',now:()=>time});await b.flush();assert.equal(s.m.size,1)});
test('stopped engine does not accept points',async()=>{const {e,store}=setup();e.stop();assert.equal(await e.accept(pos()),false);assert.equal(store.m.size,0)});
test('delete failure retains durable point',async()=>{const s=new Store();const {e}=setup(s,async()=>{s.fail=true;return {ok:true}});await e.accept(pos());await e.flush();assert.equal(s.m.size,1);assert.equal(e.state,'storage_error')});
test('unavailable geolocation cannot leave engine running',async()=>{const {e}=setup();e.running=false;e.geo=null;e.start();assert.equal(e.running,false);assert.equal(e.state,'unavailable')});
test('GPS watch callbacks are serialized to preserve distinct fixes',async()=>{const s=new Store();let callback;const e=new GpsEngineV03({store:s,api:async()=>{throw Error('offline')},geo:{watchPosition:fn=>{callback=fn;return 7},clearWatch:()=>{}},actorId:'user',deviceId:'phone',now:()=>time+30000});e.start();callback(pos(time));callback(pos(time+16000));await e.accepting;await e.flush();assert.equal(s.m.size,2);e.stop()});

test('UI position callback failure cannot discard valid durable GPS fix',async()=>{
 const store=new Store();
 const e=new GpsEngineV03({store,api:async()=>{throw Error('offline')},actorId:'user',deviceId:'phone',now:()=>time,onPosition:()=>{throw Error('broken map UI')}});
 e.running=true;
 assert.equal(await e.accept(pos()),true);
 await e.flush();
 assert.equal(store.m.size,1);
 assert.equal(e.state,'pending_sync');
});

test('status callback exceptions cannot interrupt durable capture and acknowledged sync',async()=>{
 const store=new Store();let calls=0;
 const e=new GpsEngineV03({store,api:async()=>{calls++;return {ok:true}},actorId:'user',deviceId:'phone',now:()=>time,onUpdate:()=>{throw Error('broken status UI')}});
 e.running=true;
 assert.equal(await e.accept(pos()),true);
 await e.flush();
 assert.equal(calls,1);
 assert.equal(store.m.size,0);
 assert.equal(e.state,'confirmed');
});
