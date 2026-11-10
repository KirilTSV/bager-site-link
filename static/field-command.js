/* BAGER FIELD COMMAND — progressive driver/operator GPS map. */
(()=>{
'use strict';
const role=document.body.dataset.role;
if(!['driver','operator'].includes(role))return;
const section=document.querySelector(role==='driver'?'#driverView':'#operatorView');
if(!section)return;
const card=document.createElement('section');
card.className='fc-card';
card.setAttribute('aria-label','GPS карта и диагностика');
card.innerHTML=`<div class="fc-card-header"><div><h3 class="fc-card-title">📍 Моята GPS позиция</h3><div class="fc-caption">Реална позиция само при разрешен GPS и активна страница</div></div><span class="fc-status" id="fcBadge">Не е стартиран</span></div><div id="fcMap" role="region" aria-label="Карта на последната получена GPS позиция"></div><div class="fc-tools"><button type="button" class="secondary" id="fcCenter">Центрирай</button><button type="button" class="secondary" id="fcDiagnose">Провери GPS</button></div><div class="fc-readout" id="fcReadout" aria-live="polite">Няма получена позиция.</div><div class="fc-alert" id="fcWarning">Когато телефонът се заключи, браузърното GPS проследяване може да спре.</div>`;
const controls=section.querySelector('.button-row');
if(controls)controls.insertAdjacentElement('afterend',card);else section.prepend(card);
const badge=card.querySelector('#fcBadge'),readout=card.querySelector('#fcReadout'),warning=card.querySelector('#fcWarning');
let map=null,marker=null,circle=null,lastTimestamp=0,lastCoords=null;
function setBadge(label,state=''){badge.textContent=label;badge.className='fc-status '+state}
function initMap(){if(map||!window.L)return;map=L.map('fcMap',{zoomControl:true}).setView([42.6977,23.3219],11);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);setTimeout(()=>map.invalidateSize(),200)}
function getPosition(){try{return typeof lastPosition!=='undefined'?lastPosition:null}catch{return null}}
function update(){
 initMap();const p=getPosition();
 if(!p||!p.coords){setBadge('Няма позиция','warn');readout.textContent='GPS още не е получен. Стартирай смяната и разреши местоположение.';return}
 const {latitude:lat,longitude:lon,accuracy}=p.coords,ts=Number(p.timestamp);
 if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||!Number.isFinite(ts))return;
 const age=Math.max(0,Math.round((Date.now()-ts)/1000)),fresh=age<=90;
 setBadge(fresh?'Позиция получена':'Стара позиция',fresh?'good':'warn');
 readout.textContent=`Координати: ${lat.toFixed(5)}, ${lon.toFixed(5)} · Точност: ±${Math.round(accuracy||0)} м · Възраст: ${age} сек. · Получена: ${new Date(ts).toLocaleTimeString('bg-BG')}`;
 warning.textContent=fresh?'Позицията е от телефона. Наличието ѝ на картата не доказва сървърен запис.':'Последната позиция е по-стара от 90 секунди. Не я използвай като текуща.';
 if(map&&ts!==lastTimestamp){lastTimestamp=ts;lastCoords=[lat,lon];if(!marker){marker=L.marker(lastCoords).addTo(map).bindPopup('Последна GPS позиция');circle=L.circle(lastCoords,{radius:Math.max(accuracy||0,5),color:'#ffca28',fillOpacity:.1}).addTo(map);map.setView(lastCoords,16)}else{marker.setLatLng(lastCoords);circle.setLatLng(lastCoords).setRadius(Math.max(accuracy||0,5))}}
}
card.querySelector('#fcCenter').addEventListener('click',()=>{update();if(map&&lastCoords)map.setView(lastCoords,16)});
card.querySelector('#fcDiagnose').addEventListener('click',async()=>{const secure=window.isSecureContext,supported=!!navigator.geolocation;let permission='неизвестно';try{if(navigator.permissions)permission=(await navigator.permissions.query({name:'geolocation'})).state}catch{}const p=getPosition(),age=p?Math.max(0,Math.round((Date.now()-p.timestamp)/1000)):null;window.alert(`GPS диагностика\nЗащитена връзка: ${secure?'да':'не'}\nГеолокация: ${supported?'да':'не'}\nРазрешение: ${permission}\nПоследна точка: ${age===null?'няма':age+' сек.'}\n\nБраузърното GPS проследяване може да спре при заключване на телефона.`)});
initMap();update();setInterval(update,3000);
})();