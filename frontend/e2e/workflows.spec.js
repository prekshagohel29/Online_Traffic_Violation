const API_ORIGIN=process.env.E2E_API_URL||'http://127.0.0.1:5000';
const { test, expect } = require('@playwright/test');
const fs = require('fs'); const path = require('path');
const access = JSON.parse(fs.readFileSync(path.join(__dirname,'../../data/browser-qa/access.json'),'utf8'));
async function login(page, request, role) {
  const r = await request.post(API_ORIGIN+'/api/auth/login',{data:access[role]}); expect(r.ok()).toBeTruthy(); const {access_token} = await r.json();
  await page.goto('/'); await page.evaluate(t=>sessionStorage.setItem('token',t),access_token); await page.reload();
  await expect(page.getByRole('link',{name:`QA ${role}`,exact:true})).toBeVisible(); return access_token;
}
test('portal signup and real login; production demo shortcuts absent',async({page})=>{
  await page.goto('/'); await page.getByRole('button',{name:/Vehicle Owner/}).click();
  await expect(page.getByText('Quick Access Test Accounts:')).toHaveCount(0);
  await page.getByLabel('Email address').fill(access.USER.email); await page.getByLabel('Password',{exact:true}).fill(access.USER.password);
  await page.getByRole('button',{name:'Login',exact:true}).last().click(); await expect(page.getByRole('heading',{name:'My Vehicle Control Center'})).toBeVisible();
  await page.reload(); await expect(page.getByRole('heading',{name:'My Vehicle Control Center'})).toBeVisible();
  await page.getByRole('button',{name:'Logout'}).click(); await expect(page.getByRole('heading',{name:'Welcome to e-Memo System'})).toBeVisible();
});
test('new citizen registration persists and can log in again',async({page})=>{
  const email=`browser-registration-${Date.now()}@example.test`;
  const password=require('crypto').randomBytes(18).toString('hex');
  await page.goto('/auth?role=USER'); await page.getByRole('button',{name:'Sign up',exact:true}).click();
  await page.getByLabel('Full name',{exact:true}).fill('Registration regression');
  await page.getByLabel('Email address').fill(email); await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Create citizen account'}).click();
  await expect(page.getByRole('heading',{name:'My Vehicle Control Center'})).toBeVisible();
  await page.getByRole('button',{name:'Logout'}).click();
  await page.getByRole('button',{name:/Vehicle Owner/}).click();
  await page.getByLabel('Email address').fill(email); await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Login',exact:true}).last().click();
  await expect(page.getByRole('heading',{name:'My Vehicle Control Center'})).toBeVisible();
});
test('responsive role, staff, citizen and analytics screens; direct route refresh',async({page,request})=>{
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  for(const width of [360,768,1440]){
    await page.setViewportSize({width,height:1000}); await page.goto('/'); await page.screenshot({path:`../artifacts/final-portal-${width}.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  }
  await login(page,request,'RTO');
  for(const width of [360,768,1440]){
    await page.setViewportSize({width,height:1000}); await page.goto('/rto'); await expect(page.getByRole('heading',{name:'Traffic operations, at a glance'})).toBeVisible();await expect(page.getByText('Outstanding memos',{exact:true})).toBeVisible();
    await page.screenshot({path:`../artifacts/final-rto-${width}.png`,fullPage:true}); expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  }
  await page.goto('/calibration'); await expect(page.getByRole('heading',{name:'Calibrate the road view'})).toBeVisible();
  await page.goto('/government'); await expect(page.getByRole('heading',{name:'Government Analytics & Oversight'})).toBeVisible(); await expect(page.getByText('Sandbox total',{exact:true})).toBeVisible();
  await page.screenshot({path:'../artifacts/final-analytics-1440.png',fullPage:true});
  await page.goto('/does-not-exist'); await expect(page.getByRole('heading',{name:'Page not found'})).toBeVisible();
  expect(errors).toEqual([]);
});
test('citizen cannot open staff routes; stale stored roles ignored',async({page,request})=>{
  await login(page,request,'USER'); await page.evaluate(()=>localStorage.setItem('user',JSON.stringify({role:'ADMIN'})));
  await page.goto('/admin'); await expect(page.getByRole('heading',{name:'Access restricted'})).toBeVisible();
  await page.goto('/dashboard'); await expect(page.getByRole('heading',{name:'My Vehicle Control Center'})).toBeVisible();
});
test('webcam permission denial is visible',async({page,request})=>{
  await login(page,request,'RTO'); await page.goto('/monitor');
  await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Permission denied','NotAllowedError');};});
  await page.getByRole('button',{name:'Find / allow cameras'}).click(); await expect(page.getByRole('alert')).toContainText('permission/device unavailable');
});
test('fake webcam sends actual frames; stop releases tracks',async({page,request})=>{
  const token=await login(page,request,'RTO');
  const camera=await request.post(API_ORIGIN+'/api/operator/cameras',{headers:{Authorization:`Bearer ${token}`},data:{name:'Browser fake webcam',location:'Labeled test fixture',config:{}}});
  const c=await camera.json(); await page.goto('/monitor'); await page.getByLabel('Camera / calibration').selectOption(c.id);
  await page.getByRole('button',{name:'Start webcam',exact:true}).click();
  await expect(page.getByRole('button',{name:'Stop & release camera'})).toBeEnabled();
  await expect(page.getByAltText('Analyzed source frame with aligned boxes, track IDs and source timestamp')).toBeVisible({timeout:30000});
  await page.screenshot({path:'../artifacts/final-webcam-1440.png',fullPage:true});
  await page.getByRole('button',{name:'Stop & release camera'}).click();
  await expect.poll(()=>page.locator('video').evaluate(v=>v.srcObject===null)).toBe(true);
});
test('upload progress, persisted job results, evidence and review UI',async({page,request})=>{
  test.setTimeout(180000);
  await login(page,request,'RTO'); await page.goto('/monitor');
  await page.getByLabel('Camera / calibration').selectOption({label:'CC0 rush-hour sample · v1'});
  await page.getByLabel('Video source').selectOption('upload');
  await page.getByLabel('Choose prerecorded video').setInputFiles(path.join(__dirname,'../../samples/rush-hour.webm'));
  const ticketResponse=page.waitForResponse(r=>r.url().endsWith('/api/operator/uploads') && r.request().method()==='POST');
  await page.getByRole('button',{name:'Upload & queue processing'}).click();
  const ticket=await (await ticketResponse).json();
  const newJob=page.locator(`[data-job-id="${ticket.job_id}"]`);
  await expect(newJob).toContainText('upload · COMPLETED',{timeout:150000});
  await expect(page.getByRole('link',{name:/restricted_zone · track/}).first()).toBeVisible();
  await page.getByRole('link',{name:/restricted_zone · track/}).first().click();
  await expect(page.getByRole('heading',{name:'What was recorded'})).toBeVisible();
  await expect(page.getByAltText('Case evidence image')).toBeVisible();
  await page.screenshot({path:'../artifacts/final-evidence-1440.png',fullPage:true});
  await page.getByLabel('Decision reason').fill('Browser QA: evidence inspected; deliberately configured sample zone is not a real enforcement claim.');
  await page.getByLabel('I reviewed the evidence').check(); await page.getByRole('button',{name:'Request more evidence'}).click();
  await expect(page.locator('.page-heading .status-tag')).toContainText('More evidence needed');
});
