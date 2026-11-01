export const TOKEN_GUIDE_HTML = `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vexx Cloner — как скопировать token</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0c0c12;color:#e8e8f0;font-family:"Segoe UI",system-ui,sans-serif;line-height:1.55}
.wrap{max-width:720px;margin:0 auto;padding:28px 20px 48px}
h1{font-size:1.45rem;color:#bf5fff;margin:0 0 8px}
.sub{color:#8b8ba8;margin:0 0 24px;font-size:.95rem}
a.btn{display:inline-block;background:#5865f2;color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;margin:8px 8px 8px 0}
a.btn:hover{filter:brightness(1.08)}
a.btn2{background:#2a2a3a;color:#00d9ff;border:1px solid #444}
ol{padding-left:1.2rem}
li{margin:12px 0}
code{background:#1a1a28;padding:2px 8px;border-radius:4px;color:#7ee787;font-size:.9em}
.kbd{background:#222;padding:2px 7px;border-radius:4px;border:1px solid #444;font-size:.85em}
.warn{background:#2a1818;border:1px solid #844;padding:14px;border-radius:8px;color:#faa;margin-top:24px;font-size:.9rem}
img{max-width:100%;border-radius:8px;border:1px solid #333;margin:12px 0}
.step-num{color:#00d9ff;font-weight:700}
</style>
</head>
<body>
<div class="wrap">
<h1>Как скопировать Discord user token</h1>
<p class="sub">Только для твоего аккаунта. Никому не отправляй token в чат — только форма бота <strong>/clone</strong> или <strong>/settoken</strong>.</p>

<a class="btn" href="https://discord.com/app" target="_blank" rel="noopener">1. Открыть Discord в браузере</a>
<a class="btn btn2" href="https://discord.com/app" target="_blank" rel="noopener">discord.com/app</a>

<ol>
<li><span class="step-num">Шаг 2.</span> На странице Discord нажми <span class="kbd">F12</span> (или <span class="kbd">Ctrl+Shift+I</span>) — откроются инструменты разработчика.</li>
<li><span class="step-num">Шаг 3.</span> Вкладка <strong>Сеть</strong> / <strong>Network</strong>. В фильтр сверху введи: <code>auth</code> или <code>api</code>.</li>
<li><span class="step-num">Шаг 4.</span> Нажми <span class="kbd">F5</span> (обновить страницу) или переключись на другой канал — появятся запросы к <code>discord.com</code>.</li>
<li><span class="step-num">Шаг 5.</span> Кликни любой запрос к API (например <code>science</code>, <code>messages</code>, <code>users</code>…).</li>
<li><span class="step-num">Шаг 6.</span> Справа: <strong>Заголовки</strong> / <strong>Headers</strong> → <strong>Request Headers</strong> → найди <code>authorization</code>.</li>
<li><span class="step-num">Шаг 7.</span> Скопируй <strong>значение</strong> (длинная строка). Вставь в бота в форму — <strong>не публикуй</strong> в Discord/чат.</li>
</ol>

<p>Если в заголовке есть префикс <code>Bearer</code> — для бота можно вставить всю строку или только token после пробела (бот сам обрежет).</p>

<div class="warn">
<strong>Важно:</strong> это твой полный доступ к аккаунту. Меняешь пароль / сбрасываешь сессии — token может перестать работать → снова <code>/settoken</code>.
</div>

<p style="margin-top:28px;color:#666;font-size:.85rem">Vexx Cloner Bot · после копирования вернись в Discord → <code>/clone</code></p>
</div>
</body>
</html>`;
