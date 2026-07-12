"""Generates a thin HTML report shell. All job + status data fetched from API."""

import json
from datetime import datetime

COVERAGE_TABLE = [
    ("BrighterMonday", "Yes (from Skraped)", "brightermonday.co.ke"),
    ("Glassdoor", "Yes (from Skraped)", "glassdoor.com"),
    ("LinkedIn Kenya", "Yes (JobSpy)", "linkedin.com/jobs"),
    ("Indeed Kenya", "Missing (API rejects KE)", "indeed.com"),
    ("Google Jobs", "Yes (via CDP + local Chrome)", "google.com"),
    ("ZipRecruiter", "Yes (JobSpy)", "ziprecruiter.com"),
    ("Bayt", "Yes (JobSpy)", "bayt.com"),
    ("Naukri", "Yes (JobSpy)", "naukri.com"),
    ("BDJobs", "Yes (JobSpy)", "bdjobs.com"),
    ("MyJobMag Kenya", "Yes (CDP + requests)", "myjobmag.co.ke"),
    ("Fuzu", "Yes (CDP + Playwright)", "fuzu.com"),
    ("Corporate Staffing Services", "Yes (paginated + CDP)", "corporatestaffing.co.ke"),
    ("Jobwebkenya", "Yes (CDP + Playwright)", "jobwebkenya.com"),
    ("Coding Kenya", "Yes (CDP + Playwright)", "codingkenya.com"),
    ("PigiaMe Jobs", "Yes (CDP + Playwright)", "pigiame.co.ke/jobs"),
    ("Jobiglo Kenya", "Yes (CDP + Playwright)", "ke.jobiglo.com"),
    ("GreatKenyanJobs", "Yes (CDP + Playwright)", "greatkenyanjobs.com"),
    ("CareerPoint Kenya", "Missing", "careerpointkenya.co.ke"),
    ("Turing (Kenya remote)", "Missing (bot-protected)", "turing.com"),
    ("Ajira Digital", "Missing", "ajiradigital.go.ke"),
    ("KenyaMoja", "Missing", "kenyamoja.com"),
    ("CareerJet Kenya", "Missing", "careerjet.co.ke"),
    ("Jiji Kenya", "Missing (JS-rendered)", "jiji.co.ke/jobs"),
    ("BestJobs Kenya", "Missing", "bestjobs.co.ke"),
    ("DailyJobs KE", "Missing", "dailyjobs.co.ke"),
    ("BrighterMonday Uganda", "Missing", "brightermonday.co.ug"),
    ("BeBee Kenya", "Removed (scam, subscription fee)", "bebee.com"),
    ("Expertini Kenya", "Missing (JS-heavy)", "ke.expertini.com"),
    ("WhatJobs Kenya", "Missing (JS-heavy)", "en-ke.whatjobs.com"),
    ("Kenyajob.com", "Missing (blocked)", "kenyajob.com"),
    ("Recruit.net", "Missing (blocked)", "recruit.net"),
    ("SmartRecruiters", "Missing (JS-portal)", "smartrecruiters.com"),
    ("Wellfound", "Missing (blocked)", "wellfound.com"),
    ("Talent.com KE", "Missing (aggregator)", "ke.talent.com"),
]


def build_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    coverage_json = json.dumps([{"site": s, "status": st, "url": u} for s, st, u in COVERAGE_TABLE])

    coverage_rows = "\n".join(
        f'''          <tr class="{'missing-row' if 'Missing' in st or 'Removed' in st else ''}">
            <td>{s}</td>
            <td><span class="status-pill {'yes' if st.startswith('Yes') else 'missing' if 'Missing' in st else 'removed'}">{st}</span></td>
            <td class="url">{u}</td>
          </tr>'''
        for s, st, u in COVERAGE_TABLE
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kenyan Job Finder — Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&family=Inter:wght@400;500&family=PT+Mono&display=swap" rel="stylesheet">
<style>
  :root{{
    --paper:#E9EBEE;
    --line:#D6DCE3;
    --line-strong:#9AA7B4;
    --ink:#12181F;
    --ink-soft:#5B6773;
    --green:#15803D;
    --green-soft:#DCF3E3;
    --red:#B0413E;
    --slate:#5C6B7A;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{
    background:var(--paper);
    color:var(--ink);
    font-family:'Inter',sans-serif;
    padding:64px 24px 120px;
  }}
  .page{{max-width:900px;margin:0 auto;}}

  .frame{{border:1px solid var(--line);margin-bottom:-1px;background:#fff;}}
  .frame-head{{
    border-bottom:1px solid var(--line);
    padding:10px 0;
    text-align:center;
    font-family:'PT Mono',monospace;
    font-size:11px;
    letter-spacing:0.1em;
    text-transform:uppercase;
    color:var(--ink-soft);
  }}

  .section-gap{{height:36px;}}

  /* header */
  .brand{{padding:46px 40px 40px;text-align:center;}}
  .brand small{{
    display:block;font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.15em;color:var(--green);
    text-transform:uppercase;margin-bottom:14px;
  }}
  .brand h1{{
    font-family:'IBM Plex Sans',sans-serif;font-weight:500;font-size:36px;line-height:1.1;
  }}
  .brand p{{
    font-family:'PT Mono',monospace;font-size:13px;color:var(--ink-soft);
    margin-top:16px;letter-spacing:0.01em;
  }}

  /* stats */
  .stats{{display:grid;grid-template-columns:repeat(4,1fr);}}
  .stat{{padding:34px 28px;border-right:1px solid var(--line);}}
  .stat:last-child{{border-right:none;}}
  .stat .label{{
    font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--green);margin-bottom:14px;
  }}
  .stat .value{{
    font-family:'IBM Plex Sans',sans-serif;font-weight:500;font-size:32px;color:var(--ink);
  }}
  .stat .value.small{{font-size:20px;}}
  .stat .value.gap{{color:var(--slate);font-size:17px;font-family:'PT Mono',monospace;}}

  /* sources */
  .src-meta{{display:flex;justify-content:space-between;align-items:baseline;padding:30px 50px 0;}}
  .src-meta h2{{font-family:'IBM Plex Sans',sans-serif;font-weight:500;font-size:18px;}}
  .src-meta .count{{font-family:'PT Mono',monospace;font-size:12px;color:var(--ink-soft);}}

  .bars{{padding:22px 50px 8px;}}
  .bar-row{{display:flex;align-items:center;gap:16px;padding:9px 0;border-bottom:1px solid var(--line);}}
  .bar-row:last-child{{border-bottom:none;}}
  .bar-row .name{{
    flex:0 0 190px;font-family:'IBM Plex Sans',sans-serif;font-size:13.5px;color:var(--ink);
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  }}
  .bar-track{{flex:1;background:#EAEDF1;border:1px solid var(--line);border-radius:3px;height:16px;}}
  .bar-fill{{height:100%;background:var(--green);border-radius:2px;}}
  .bar-row .count{{flex:0 0 34px;text-align:right;font-family:'PT Mono',monospace;font-size:12.5px;color:var(--ink-soft);}}
  .bar-row.other .bar-fill{{background:var(--ink-soft);}}

  .pagination{{display:flex;align-items:center;justify-content:space-between;padding:18px 50px 34px;}}
  .page-info{{font-family:'PT Mono',monospace;font-size:11.5px;color:var(--ink-soft);letter-spacing:0.02em;}}
  .page-controls{{display:flex;align-items:center;gap:6px;}}
  .page-btn{{
    background:#fff;border:1px solid var(--line-strong);border-radius:6px;
    font-family:'PT Mono',monospace;font-size:11.5px;color:var(--ink);
    width:30px;height:30px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;
  }}
  .page-btn:hover:not(:disabled){{background:var(--green-soft);border-color:var(--green);color:var(--green);}}
  .page-btn:disabled{{opacity:0.35;cursor:default;}}
  .page-btn.nav svg{{width:9px;height:9px;stroke:currentColor;}}
  .page-btn.active{{background:var(--green);border-color:var(--green);color:#fff;}}

  /* tabs */
  .tabs{{display:flex;}}
  .tab{{
    flex:1;font-family:'PT Mono',monospace;font-size:12px;letter-spacing:0.03em;
    padding:18px 20px;color:var(--ink-soft);text-align:center;border-right:1px solid var(--line);cursor:pointer;
  }}
  .tab:last-child{{border-right:none;}}
  .tab .n{{color:var(--ink-soft);}}
  .tab.active{{color:var(--green);background:var(--green-soft);}}
  .tab.active .n{{color:var(--green);}}

  /* filters */
  .filters{{display:grid;grid-template-columns:1fr 1fr;}}
  .field{{padding:24px 32px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);}}
  .field:nth-child(2n){{border-right:none;}}
  .filters .field:last-child, .filters .field:nth-last-child(2){{border-bottom:none;}}
  .field label{{
    display:block;font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--green);margin-bottom:10px;
  }}
  .field input, .field select{{
    width:100%;border:1px solid var(--line);border-radius:5px;padding:10px 13px;
    font-family:'IBM Plex Sans',sans-serif;font-size:13.5px;color:var(--ink);background:#fff;
  }}
  .field input::placeholder{{color:#A4ABB3;}}
  .loc-row{{display:flex;gap:12px;align-items:center;}}
  .loc-row input{{flex:1;}}
  .shown-pill{{
    flex:0 0 auto;font-family:'PT Mono',monospace;font-size:11.5px;color:var(--ink-soft);
    border:1px solid var(--line);border-radius:5px;padding:10px 13px;white-space:nowrap;
  }}

  /* job list */
  .job-list{{padding:0;background:#fff;}}
  .job-row{{padding:26px 44px;border-bottom:1px solid var(--line);}}
  .job-row:last-child{{border-bottom:none;}}
  .job-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;}}
  .job-title{{font-family:'IBM Plex Sans',sans-serif;font-weight:500;font-size:16px;color:var(--ink);}}
  .job-source{{
    font-family:'PT Mono',monospace;font-size:10.5px;color:var(--ink-soft);
    letter-spacing:0.03em;white-space:nowrap;padding-top:3px;
  }}
  .job-meta{{font-family:'PT Mono',monospace;font-size:12px;color:var(--ink-soft);margin-top:8px;}}
  .job-desc{{
    font-family:'IBM Plex Sans',sans-serif;font-size:13px;line-height:1.65;color:var(--ink-soft);
    margin-top:12px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  }}
  .job-bottom{{display:flex;justify-content:space-between;align-items:center;margin-top:18px;}}
  .job-date{{font-family:'PT Mono',monospace;font-size:11.5px;color:var(--ink-soft);display:flex;align-items:center;gap:16px;}}
  .job-date a{{color:var(--green);text-decoration:none;font-weight:600;}}
  .job-date .nodate{{color:#B8BEC5;}}

  .job-actions{{display:flex;gap:8px;}}
  .toggle-btn{{
    font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.02em;
    padding:7px 14px;border-radius:5px;cursor:pointer;
    background:#EEF0F2;color:var(--ink-soft);border:1px solid var(--line-strong);
  }}
  .toggle-btn:hover{{border-color:var(--ink);color:var(--ink);background:#E4E7EA;}}
  .toggle-btn.on{{background:var(--ink);color:#fff;border-color:var(--ink);}}

  .empty{{
    text-align:center;padding:60px 20px;
    font-family:'IBM Plex Sans',sans-serif;color:var(--ink-soft);
  }}
  .empty .big{{font-size:20px;margin-bottom:8px;}}

  /* coverage */
  .coverage-head{{padding:30px 50px 22px;}}
  .coverage-head h2{{font-family:'IBM Plex Sans',sans-serif;font-weight:500;font-size:18px;}}
  .coverage-head p{{font-family:'PT Mono',monospace;font-size:12.5px;color:var(--ink-soft);margin-top:6px;}}

  .cov-table{{width:100%;border-collapse:collapse;}}
  .cov-table th{{
    text-align:left;
    font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--green);padding:0 50px 14px;border-bottom:1px solid var(--line);
  }}
  .cov-table td{{
    padding:14px 50px;border-bottom:1px solid var(--line);
    font-family:'IBM Plex Sans',sans-serif;font-size:13.5px;color:var(--ink);
    vertical-align:middle;
  }}
  .cov-table tr:last-child td{{border-bottom:none;}}
  .cov-table tr.missing-row td{{color:var(--ink-soft);}}
  .cov-table td.url{{
    font-family:'PT Mono',monospace;font-size:12.5px;color:var(--ink-soft);
  }}
  .cov-table tr.missing-row td.url{{color:#B8BEC5;}}

  .status-pill{{
    display:inline-block;
    font-family:'PT Mono',monospace;font-size:11px;letter-spacing:0.02em;
    padding:5px 11px;border-radius:3px;
    background:#fff;border:1px solid var(--line-strong);
  }}
  .status-pill.yes{{color:#0F3D66;border-color:#3E7CB8;background:#BFDBF3;}}
  .status-pill.missing{{color:#7A241F;border-color:#C96760;background:#F5C9C5;}}
  .status-pill.removed{{color:#7A241F;border-color:#C96760;background:#F5C9C5;}}

  @media(max-width:700px){{
    .stats{{grid-template-columns:repeat(2,1fr);}}
    .stat:nth-child(2){{border-right:none;}}
    .stat:nth-child(1),.stat:nth-child(2){{border-bottom:1px solid var(--line);}}
    .filters{{grid-template-columns:1fr;}}
    .field{{border-right:none;}}
    .job-top{{flex-direction:column;}}
    .job-row{{padding:22px 24px;}}
    .brand h1{{font-size:26px;}}
    .bar-row .name{{flex-basis:130px;}}
    .cov-table th, .cov-table td{{padding-left:24px;padding-right:24px;}}
    .cov-table{{font-size:12px;}}
  }}
</style>
</head>
<body>
<div class="page">

  <div class="frame">
    <div class="frame-head">Jobs pipeline — aggregator feed</div>
    <div class="brand">
      <small>Kenya market</small>
      <h1>Kenyan Job Finder</h1>
      <p id="header-sub">Loading...</p>
    </div>
  </div>

  <div class="frame">
    <div class="frame-head">Overview</div>
    <div class="stats">
      <div class="stat">
        <div class="label">Total jobs</div>
        <div class="value" id="total-count">—</div>
      </div>
      <div class="stat">
        <div class="label">Sources</div>
        <div class="value" id="source-count">—</div>
      </div>
      <div class="stat">
        <div class="label">Earliest</div>
        <div class="value small" id="date-earliest">—</div>
      </div>
      <div class="stat">
        <div class="label">Latest</div>
        <div class="value gap" id="date-latest">—</div>
      </div>
    </div>
  </div>

  <div class="frame">
    <div class="frame-head">Jobs per source</div>
    <div class="src-meta">
      <h2>Top sources by volume</h2>
      <div class="count" id="source-meta-count"></div>
    </div>
    <div class="bars" id="bar-list"></div>
    <div class="pagination">
      <div class="page-info" id="pageInfo"></div>
      <div class="page-controls" id="pageControls"></div>
    </div>
  </div>

  <div class="section-gap"></div>

  <div class="frame">
    <div class="frame-head">Job tracker — application pipeline</div>
    <div class="tabs" id="tab-bar">
      <div class="tab active" data-tab="all">All Jobs <span class="n" id="count-all"></span></div>
      <div class="tab" data-tab="applied">Applied <span class="n" id="count-applied"></span></div>
      <div class="tab" data-tab="ignored">Ignored <span class="n" id="count-ignored"></span></div>
    </div>
  </div>

  <div class="frame">
    <div class="frame-head">Refine results</div>
    <div class="filters">
      <div class="field">
        <label>Search</label>
        <input type="text" id="search-input" placeholder="Title, company, keyword...">
      </div>
      <div class="field">
        <label>Source</label>
        <select id="source-filter"><option value="all">All sources</option></select>
      </div>
      <div class="field">
        <label>Location</label>
        <div class="loc-row">
          <input type="text" id="location-filter" placeholder="Nairobi, remote...">
          <div class="shown-pill" id="filter-count">0 shown</div>
        </div>
      </div>
      <div class="field"></div>
    </div>
  </div>

  <div class="frame">
    <div class="frame-head">Results</div>
    <div class="job-list" id="job-list"></div>
  </div>

  <div class="section-gap"></div>

  <div class="frame">
    <div class="frame-head">Aggregator coverage</div>
    <div class="coverage-head">
      <h2>Aggregator Coverage</h2>
      <p>Kenya job boards and aggregators.</p>
    </div>
    <table class="cov-table">
      <thead>
        <tr>
          <th>Site</th>
          <th>Status</th>
          <th>URL</th>
        </tr>
      </thead>
      <tbody>
{coverage_rows}
      </tbody>
    </table>
  </div>

</div>

<script>
const API_BASE = 'http://127.0.0.1:9090';

let JOBS = [];
let currentTab = 'all';

/* ---------- source bars, paginated ---------- */
const PAGE_SIZE = 10;
let currentPage = 1;
let sourceData = [];

function makeBarRow(name, count, maxCount){{
  const row = document.createElement('div');
  row.className = 'bar-row' + (count <= 8 ? ' other' : '');
  const pct = Math.max((count / maxCount * 100), 2).toFixed(1);
  row.innerHTML =
    '<div class="name">' + name + '</div>' +
    '<div class="bar-track"><div class="bar-fill" style="width:' + pct + '%"></div></div>' +
    '<div class="count">' + count + '</div>';
  return row;
}}

function renderSourcePage(page){{
  currentPage = page;
  const container = document.getElementById('bar-list');
  container.innerHTML = '';
  const totalPages = Math.ceil(sourceData.length / PAGE_SIZE);
  const start = (page - 1) * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, sourceData.length);
  const maxVal = sourceData[0][1];
  sourceData.slice(start, end).forEach(function(d){{
    container.appendChild(makeBarRow(d[0], d[1], maxVal));
  }});
  document.getElementById('pageInfo').textContent = 'Showing ' + (start + 1) + '\\u2013' + end + ' of ' + sourceData.length;
  renderPageControls(totalPages);
}}

function renderPageControls(totalPages){{
  const el = document.getElementById('pageControls');
  el.innerHTML = '';

  var prev = document.createElement('button');
  prev.className = 'page-btn nav';
  prev.disabled = currentPage === 1;
  prev.innerHTML = '<svg viewBox="0 0 10 10" fill="none"><path d="M6.5 1.5L2.5 5l4 3.5" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  prev.addEventListener('click', function(){{ renderSourcePage(currentPage - 1); }});
  el.appendChild(prev);

  for(var i = 1; i <= totalPages; i++){{
    var btn = document.createElement('button');
    btn.className = 'page-btn' + (i === currentPage ? ' active' : '');
    btn.textContent = i;
    btn.addEventListener('click', (function(p){{ return function(){{ renderSourcePage(p); }}; }})(i));
    el.appendChild(btn);
  }}

  var next = document.createElement('button');
  next.className = 'page-btn nav';
  next.disabled = currentPage === totalPages;
  next.innerHTML = '<svg viewBox="0 0 10 10" fill="none"><path d="M3.5 1.5L7.5 5l-4 3.5" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  next.addEventListener('click', function(){{ renderSourcePage(currentPage + 1); }});
  el.appendChild(next);
}}

/* ---------- render ---------- */
function renderSummary(){{
  document.getElementById('total-count').textContent = JOBS.length;
  const sources = new Set(JOBS.map(function(j){{ return j.source; }}));
  document.getElementById('source-count').textContent = sources.size;
  const dates = JOBS.map(function(j){{ return j.date_posted; }}).filter(Boolean).sort();
  document.getElementById('date-earliest').textContent = dates[0] ? dates[0].slice(0, 10) : '\\u2014';
  document.getElementById('date-latest').textContent = dates[dates.length - 1] ? dates[dates.length - 1].slice(0, 10) : '\\u2014';
  document.getElementById('header-sub').textContent = sources.size + ' sources tracked';

  // build source data for bars
  var counts = {{}};
  JOBS.forEach(function(j){{ counts[j.source] = (counts[j.source] || 0) + 1; }});
  sourceData = Object.entries(counts).sort(function(a,b){{ return b[1] - a[1]; }});
  document.getElementById('source-meta-count').textContent = sourceData.length + ' sources \\u00b7 ' + JOBS.length + ' jobs';
  renderSourcePage(1);
}}

function renderJobs(jobs){{
  const container = document.getElementById('job-list');
  if (!jobs.length){{
    container.innerHTML = '<div class="empty"><div class="big">No jobs match your filters</div><p>Try widening your search criteria</p></div>';
    return;
  }}
  var html = '';
  for(var i = 0; i < jobs.length; i++){{
    var j = jobs[i];
    var date = (j.date_posted || '').slice(0, 10);
    var desc = (j.description || '').slice(0, 300);
    var location = j.location || '\\u2014';
    var company = j.company || 'Unknown';
    var url = j.url || '#';
    var title = j.title || 'Untitled';
    var st = j.status || '';
    var appliedOn = st === 'applied' ? ' on' : '';
    var ignoredOn = st === 'ignored' ? ' on' : '';
    var meta = company + ' \\u00b7 ' + location;

    html += '<div class="job-row">' +
      '<div class="job-top">' +
        '<div class="job-title">' + title + '</div>' +
        '<div class="job-source">' + j.source + '</div>' +
      '</div>' +
      '<div class="job-meta">' + meta + '</div>' +
      (desc ? '<div class="job-desc">' + desc + '</div>' : '') +
      '<div class="job-bottom">' +
        '<div class="job-date">' +
          (date ? date : '<span class="nodate">no date</span>') +
          ' <a href="' + url + '" target="_blank">View job \\u2192</a>' +
        '</div>' +
        '<div class="job-actions">' +
          '<button class="toggle-btn applied-btn' + appliedOn + '" data-url="' + encodeURIComponent(url) + '">Applied</button>' +
          '<button class="toggle-btn ignore-btn' + ignoredOn + '" data-url="' + encodeURIComponent(url) + '">Ignore</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }}
  container.innerHTML = html;
}}

function applyFilters(){{
  const search = document.getElementById('search-input').value.toLowerCase();
  const source = document.getElementById('source-filter').value;
  const location = document.getElementById('location-filter').value.toLowerCase();

  var filtered = JOBS.filter(function(j){{
    const text = (j.title + ' ' + j.company + ' ' + (j.description || '')).toLowerCase();
    if (search && !text.includes(search)) return false;
    if (source !== 'all' && j.source !== source) return false;
    if (location && !(j.location || '').toLowerCase().includes(location)) return false;
    const s = j.status || '';
    if (currentTab === 'applied' && s !== 'applied') return false;
    if (currentTab === 'ignored' && s !== 'ignored') return false;
    if (currentTab === 'all' && s) return false;
    return true;
  }});

  document.getElementById('filter-count').textContent = filtered.length + ' shown';

  var allC = 0, appC = 0, ignC = 0;
  JOBS.forEach(function(j){{
    const s = j.status || '';
    if (!s) allC++; else if (s === 'applied') appC++; else if (s === 'ignored') ignC++;
  }});
  document.getElementById('count-all').textContent = '(' + allC + ')';
  document.getElementById('count-applied').textContent = '(' + appC + ')';
  document.getElementById('count-ignored').textContent = '(' + ignC + ')';

  renderJobs(filtered);
}}

/* ---------- status toggles ---------- */
document.getElementById('job-list').addEventListener('click', function(e){{
  var btn = e.target.closest('.toggle-btn');
  if (!btn) return;
  var urlEnc = btn.dataset.url;
  var url = decodeURIComponent(urlEnc);
  var job = JOBS.find(function(j){{ return j.url === url; }});
  if (!job) return;

  var isApplied = btn.classList.contains('applied-btn');
  var wasOn = btn.classList.contains('on');

  var row = btn.closest('.job-row');
  var appBtn = row.querySelector('.applied-btn');
  var ignBtn = row.querySelector('.ignore-btn');

  if (isApplied){{
    if (wasOn){{ job.status = null; appBtn.classList.remove('on'); }}
    else {{ job.status = 'applied'; appBtn.classList.add('on'); ignBtn.classList.remove('on'); }}
  }} else {{
    if (wasOn){{ job.status = null; ignBtn.classList.remove('on'); }}
    else {{ job.status = 'ignored'; ignBtn.classList.add('on'); appBtn.classList.remove('on'); }}
  }}

  fetch(API_BASE + '/api/status', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{url: url, status: job.status}})
  }}).catch(function(){{}});

  applyFilters();
}});

/* ---------- tab switching ---------- */
document.getElementById('tab-bar').addEventListener('click', function(e){{
  var tab = e.target.closest('.tab');
  if (!tab) return;
  currentTab = tab.dataset.tab;
  document.querySelectorAll('.tab').forEach(function(t){{
    t.classList.toggle('active', t.dataset.tab === currentTab);
  }});
  applyFilters();
}});

/* ---------- filter events ---------- */
document.getElementById('search-input').addEventListener('input', applyFilters);
document.getElementById('source-filter').addEventListener('change', applyFilters);
document.getElementById('location-filter').addEventListener('input', applyFilters);

/* ---------- init ---------- */
async function init(){{
  try {{
    const resp = await fetch(API_BASE + '/api/jobs');
    JOBS = await resp.json();
  }} catch(e){{
    document.getElementById('job-list').innerHTML = '<div class="empty"><div class="big">API unavailable</div><p>Start the API server: python api.py --port 9090</p></div>';
    return;
  }}
  // add source options
  var sources = new Set(JOBS.map(function(j){{ return j.source; }}));
  var sel = document.getElementById('source-filter');
  sources.forEach(function(s){{
    var opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  }});
  renderSummary();
  applyFilters();
}}

init();
</script>
</body>
</html>'''

