const API_ORIGIN=process.env.E2E_API_URL||'http://127.0.0.1:5000';
const {test,expect}=require('@playwright/test');
const fs=require('fs');const path=require('path');
const access=JSON.parse(fs.readFileSync(path.join(__dirname,'../../data/browser-qa/test-access.json'),'utf8'));
async function login(page,request,role){const r=await request.post(API_ORIGIN+'/api/auth/login',{data:access[role]});expect(r.ok()).toBeTruthy();const data=await r.json();await page.goto('/');await page.evaluate(t=>sessionStorage.setItem('token',t),data.access_token);await page.goto(role==='USER'?'/dashboard':role==='GOVT'?'/government':'/rto');return data.access_token;}
test('dataset evidence, RTO memo, correct citizen payment and private government summary',async({page,request})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await login(page,request,'RTO');await expect(page.getByText('Outstanding memos',{exact:true})).toBeVisible();await page.screenshot({path:'../artifacts/showcase-overview.png',fullPage:true});
 await page.goto('/datasets');await expect(page.getByAltText('Helmet safety dataset · image 0')).toBeVisible();await expect(page.getByRole('button',{name:'Compare model & labels'})).toHaveCount(0);await page.screenshot({path:'../artifacts/college-datasets.png',fullPage:true});
 await page.getByRole('button',{name:'Create practice case'}).first().click();await expect(page.getByAltText('Case evidence image')).toBeVisible();const caseURL=page.url();
 await page.getByLabel('Decision reason').fill('Browser regression: attributed dataset evidence reviewed with an explicitly fictional owner association.');await page.getByLabel('I reviewed the evidence').check();await page.getByRole('button',{name:'Confirm case & issue memo'}).click();await expect(page.getByText('LINKED PROJECT MEMO')).toBeVisible();await page.screenshot({path:'../artifacts/showcase-case.png',fullPage:true});
 await login(page,request,'USER');await page.goto(caseURL);await expect(page.getByRole('button',{name:'Record sandbox payment'})).toBeVisible();await page.getByRole('button',{name:'Record sandbox payment'}).click();await expect(page.getByText('Sandbox receipt recorded. No real money was transferred.')).toBeVisible();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download memo / receipt'}).first().click();expect((await download).suggestedFilename()).toContain('.pdf');
 await login(page,request,'GOVT');await expect(page.getByText('Sandbox total',{exact:true})).toBeVisible();await page.goto(caseURL);await expect(page.getByRole('heading',{name:'Restricted for privacy'})).toBeVisible();await expect(page.getByAltText('Case evidence image')).toHaveCount(0);await expect(page.getByText('GJ00DM1001',{exact:true})).toHaveCount(0);expect(errors).toEqual([]);
});
test('included traffic video starts without a manual file upload',async({page,request})=>{
 test.setTimeout(150000);await login(page,request,'RTO');await page.goto('/monitor');
 await expect(page.getByRole('button',{name:'Analyse included traffic video'})).toBeEnabled();
 const response=page.waitForResponse(r=>r.url().endsWith('/api/samples/rush-hour/run')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Analyse included traffic video'}).click();const result=await response;expect(result.ok()).toBeTruthy();const job=await result.json();
 await expect(page.locator(`[data-job-id="${job.job_id}"]`)).toContainText('upload · COMPLETED',{timeout:120000});
 await expect(page.getByRole('link',{name:/restricted_zone · track/}).first()).toBeVisible();
});

test('college screens expose working inputs and searchable case references',async({page,request})=>{
 await login(page,request,'RTO');await page.goto('/monitor');
 await expect(page.getByLabel('Video source').locator('option')).toHaveCount(2);
 await expect(page.getByLabel('Video source').locator('option[value="ip"]')).toHaveCount(0);
 await page.goto('/calibration');await expect(page.getByText('Advanced thresholds and timing',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Minimum movement duration (s)')).toBeHidden();
 await page.goto('/cases?scope=demo');await expect(page.getByRole('button',{name:'Demo examples',exact:true})).toHaveAttribute('aria-pressed','true');
 const reference=await page.locator('.case-ref').first().textContent();await page.getByLabel('Search cases').fill(reference);
 await expect(page.locator('.case-table tbody tr')).toHaveCount(1);await expect(page.locator('.case-ref')).toHaveText(reference);
});

test('analytics has usable filters and administration has a clear service summary',async({page,request})=>{
 await login(page,request,'GOVT');await page.goto('/government');
 await expect(page.getByLabel('Violation type').locator('option')).not.toHaveCount(1);
 await page.getByLabel('Violation type').selectOption('Helmet Violation');await expect(page.getByText('Sandbox total',{exact:true})).toBeVisible();
 await page.getByLabel('From (IST)').fill('2026-11-06');await page.getByLabel('Through (IST)').fill('2026-11-05');
 await expect(page.getByRole('alert')).toContainText('end date');await page.getByRole('button',{name:'Clear filters'}).click();
 await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByText('Sandbox total',{exact:true})).toBeVisible();
 await login(page,request,'ADMIN');await page.goto('/admin');await page.getByRole('button',{name:'Service health',exact:true}).click();
 await expect(page.getByRole('heading',{name:'How processing works'})).toBeVisible();await expect(page.getByText('Video analysis',{exact:true}).last()).toBeVisible();
 await page.screenshot({path:'../artifacts/college-service-health.png',fullPage:true});
});
