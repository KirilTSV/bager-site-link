/* BAGER GPS v0.3 — durable queue, no third-party dependencies. */
export class IndexedGpsStore {
  constructor(name='bager-gps-v03'){this.name=name;this.dbPromise=null;}
  async db(){
    if(this.dbPromise)return this.dbPromise;
    this.dbPromise=new Promise((resolve,reject)=>{
      if(!globalThis.indexedDB){reject(Error('IndexedDB unavailable'));return;}
      const r=indexedDB.open(this.name,1);
      r.onupgradeneeded=()=>{const db=r.result;if(!db.objectStoreNames.contains('points'))db.createObjectStore('points',{keyPath:'id'});};
      r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error||Error('IndexedDB open failed'));
      r.onblocked=()=>reject(Error('IndexedDB blocked'));
    }).catch(e=>{this.dbPromise=null;throw e});return this.dbPromise;
  }
  async transact(mode,fn){const db=await this.db();return new Promise((resolve,reject)=>{
    const tx=db.transaction('points',mode),store=tx.objectStore('points');let result;
    try{result=fn(store)}catch(e){tx.abort();reject(e);return}
    tx.oncomplete=()=>resolve(result);tx.onerror=()=>reject(tx.error||Error('IndexedDB transaction failed'));tx.onabort=()=>reject(tx.error||Error('IndexedDB aborted'));
  });}
  put(item){return this.transact('readwrite',s=>{s.put(item)});}
  remove(id){return this.transact('readwrite',s=>{s.delete(id)});}
  async list(prefix){const db=await this.db();return new Promise((resolve,reject)=>{
    const tx=db.transaction('points','readonly'),req=tx.objectStore('points').getAll();let items;
    req.onsuccess=()=>{items=req.result.filter(x=>typeof x.id==='string'&&x.id.startsWith(prefix)).sort((a,b)=>a.created-b.created)};
    tx.oncomplete=()=>resolve(items||[]);
    tx.onerror=()=>reject(tx.error||Error('IndexedDB read failed'));
    tx.onabort=()=>reject(tx.error||Error('IndexedDB read aborted'));
  });}
}
export class GpsEngineV03 {
  constructor({store,api,geo,actorId,deviceId,now=()=>Date.now(),onUpdate=()=>{},onPosition=()=>{},interval=15000,maxPending=500}={}){
    if(!store||!api||!actorId||!deviceId)throw Error('Missing GPS engine dependency');
    Object.assign(this,{store,api,geo,actorId,deviceId,now,onUpdate,onPosition,interval,maxPending});
    this.prefix=`${actorId}:${deviceId}:`;this.sequence=0;this.watchId=null;this.running=false;this.accepting=Promise.resolve();this.lastRecorded=-Infinity;this.flushing=null;this.state='idle';this.lastConfirmed=null;this.error=null;this.pending=null;
  }
  emit(state,error=null){this.state=state;this.error=error;this.onUpdate({state,error,pending:this.pending,lastConfirmed:this.lastConfirmed});}
  async count(){const list=await this.store.list(this.prefix);this.pending=list.length;return list.length;}
  async accept(pos){
    if(!this.running)return false;
    const c=pos?.coords,t=Number(pos?.timestamp),now=this.now();
    if(!c||![c.latitude,c.longitude,c.accuracy,t].every(Number.isFinite)||Math.abs(c.latitude)>90||Math.abs(c.longitude)>180||c.accuracy<0||c.accuracy>10000||t>now+120000||t<now-48*3600000){this.emit('invalid_fix');return false;}
    this.onPosition({latitude:c.latitude,longitude:c.longitude,accuracy:c.accuracy,timestamp:t});
    if(t-this.lastRecorded<this.interval)return true;
    try{
      if(await this.count()>=this.maxPending){this.emit('queue_full');return false;}
      const nonce=globalThis.crypto?.randomUUID?.()||`${t}-${++this.sequence}`;
      const id=this.prefix+t+":"+nonce;
      const point={id,created:t,payload:{latitude:c.latitude,longitude:c.longitude,accuracy_m:c.accuracy,speed_mps:Number.isFinite(c.speed)&&c.speed>=0&&c.speed<=150?c.speed:null,heading_deg:Number.isFinite(c.heading)&&c.heading>=0&&c.heading<=360?c.heading:null,recorded_at:new Date(t).toISOString(),device_event_id:`gps-${nonce}`}};
      await this.store.put(point);this.lastRecorded=t;this.pending++;this.emit('durable');void this.flush();return true;
    }catch(e){this.emit('storage_error',String(e));return false;}
  }
  async flush(){
    if(this.flushing)return this.flushing;
    const locks=globalThis.navigator?.locks;
    const work=()=>this._flush();
    const promise=Promise.resolve().then(()=>locks?.request
      ? locks.request(`bager-gps-sync:${this.prefix}`,{mode:'exclusive'},work)
      : work()).catch(e=>{this.emit('sync_error',String(e));return false});
    this.flushing=promise.finally(()=>{this.flushing=null});
    return this.flushing;
  }
  async _flush(){
    try{const points=await this.store.list(this.prefix);this.pending=points.length;
      for(const point of points){
        this.emit('uploading');let response;
        try{response=await this.api('/api/gps',{method:'POST',body:JSON.stringify(point.payload)});}catch(e){this.emit('pending_sync',String(e));return false;}
        if(response?.ok!==true){this.emit('pending_sync','No server acknowledgement');return false;}
        await this.store.remove(point.id);this.pending--;this.lastConfirmed=this.now();this.emit('confirmed');
      }return true;
    }catch(e){this.emit('storage_error',String(e));return false;}
  }
  start(){if(this.running)return;this.running=true;if(!this.geo?.watchPosition){this.running=false;this.emit('unavailable');return;}
    this.emit('requesting_permission');try{this.watchId=this.geo.watchPosition(p=>{this.accepting=this.accepting.then(()=>this.accept(p)).catch(e=>this.emit('storage_error',String(e)))},e=>this.emit(e?.code===1?'permission_denied':'gps_error',e?.message),{enableHighAccuracy:true,maximumAge:10000,timeout:20000});}catch(e){this.running=false;this.emit('gps_error',String(e));}
    void this.flush();
  }
  stop(){this.running=false;if(this.watchId!==null)this.geo?.clearWatch?.(this.watchId);this.watchId=null;this.emit('stopped');}
}
