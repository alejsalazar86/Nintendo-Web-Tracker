import time
import sqlite3
import os
import threading
import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, url_for, jsonify, session, redirect
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# CAMBIO IMPORTANTE: static_folder='.' indica que las imágenes están en la raíz
app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'nintendo_super_secret_key_2026')

# CREDENCIALES
ADMIN_USER = "ALEJSALAZAR"
ADMIN_PASS = "Aj17694sr448"

# ESTADO GLOBAL
TASK_STATUS = {'percent': 0, 'status': 'Listo', 'running': False}

# --- CSS GLOBAL ---
COMMON_CSS = '''
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@900&display=swap" rel="stylesheet">
<style>
    :root { 
        --transition-speed: 0.3s;
        --bg-color: #202020; --sidebar-bg: #2a2a2a; --card-bg: #333333;
        --text-color: #ffffff; --input-bg: #444444; --border-color: #555;
    }
    html.light-mode body {
        --bg-color: #f0f2f5; --sidebar-bg: #ffffff; --card-bg: #ffffff;
        --text-color: #1c1e21; --input-bg: #f0f2f5; --border-color: #ccc;
    }
    body.section-sw1 { --accent: #00b0ed; }
    body.section-sw2 { --accent: #e60012; }
    body.section-offers { --accent: #ffae00; }
    body.section-bestsellers { --accent: #8b0000; }
    
    body { font-family: 'Segoe UI', sans-serif; background: var(--bg-color); color: var(--text-color); margin: 0; padding: 0; transition: background var(--transition-speed), color var(--transition-speed); }
    
    .theme-toggle-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; padding: 5px; color: var(--text-color); }
    .theme-toggle-btn:hover { transform: scale(1.2); }

    .main-header { background: var(--accent); color: white; padding: 25px; text-align: center; position: relative; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .admin-btn { position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.2); color: white; text-decoration: none; padding: 8px 15px; border-radius: 20px; font-weight: bold; border: 1px solid rgba(255,255,255,0.3); backdrop-filter: blur(5px); }
    .admin-btn:hover { background: rgba(255,255,255,0.3); }

    .gamer-subtitle { font-family: 'Cinzel', serif; font-size: 2.5em; margin-top: 10px; color: #fff; text-shadow: 2px 2px 0px #000; letter-spacing: 2px; text-transform: uppercase; }

    .login-container { max-width: 400px; margin: 100px auto; background: var(--sidebar-bg); padding: 40px; border-radius: 15px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .login-input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 5px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--text-color); }
    .login-btn { width: 100%; padding: 12px; background: var(--accent); color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 20px; }
    .error-msg { color: #ff4d4d; margin-top: 10px; font-size: 0.9em; }

    .selection-container { display: flex; justify-content: center; gap: 30px; margin-top: 50px; flex-wrap: wrap; padding: 20px; }
    .option-card { background: var(--card-bg); border-radius: 20px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 300px; transition: transform 0.3s; text-decoration: none; color: var(--text-color); display: block; border: 2px solid transparent; }
    .option-card:hover { transform: translateY(-10px); border-color: var(--accent); }
    .option-img-container { width: 100%; height: 180px; background: #fff; display: flex; align-items: center; justify-content: center; padding: 20px; box-sizing: border-box; }
    .option-img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
    .option-title { padding: 15px; font-size: 1.4em; font-weight: bold; background: var(--sidebar-bg); text-align: center; }
    .last-update { font-size: 0.8em; color: #888; padding-bottom: 15px; background: var(--sidebar-bg); text-align: center; }

    .admin-panel { max-width: 750px; margin: 40px auto; background: var(--sidebar-bg); padding: 40px; border-radius: 15px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    .form-group { margin-bottom: 25px; text-align: left; }
    .form-group label { display: block; margin-bottom: 10px; font-size: 1.2em; }
    .form-group select { width: 100%; padding: 15px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 1.1em; background: var(--input-bg); color: var(--text-color); }
    .btn-update { padding: 15px 30px; border: none; border-radius: 50px; font-size: 1.2em; cursor: pointer; color: white; font-weight: bold; width: 100%; margin-top: 10px; transition: transform 0.2s; }
    .btn-update:hover { transform: scale(1.05); }
    
    .status-table { width: 100%; margin-top: 40px; border-collapse: collapse; background: var(--input-bg); border-radius: 10px; overflow: hidden; }
    .status-table th, .status-table td { padding: 15px; text-align: left; border-bottom: 1px solid var(--border-color); }
    .status-table th { background: rgba(0,0,0,0.2); font-weight: bold; color: var(--accent); }
    .row-outdated { color: #ff4d4d !important; font-weight: bold; }

    #progress-container { display: none; margin-top: 30px; background: #111; border-radius: 10px; padding: 20px; }
    .progress-bar-bg { width: 100%; height: 25px; background: #444; border-radius: 15px; overflow: hidden; margin-top: 10px; }
    .progress-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #e60012, #ff4d4d); transition: width 0.5s ease; }
</style>
<script>
    (function() {
        let state = localStorage.getItem('global_theme_state');
        if (state === '1') { document.documentElement.classList.add('light-mode'); } 
        else { document.documentElement.classList.remove('light-mode'); }
    })();

    function toggleGlobalTheme() {
        document.documentElement.classList.toggle('light-mode');
        let isLight = document.documentElement.classList.contains('light-mode');
        localStorage.setItem('global_theme_state', isLight ? '1' : '0');
        updateIcon();
    }
    
    function updateIcon() {
        const icon = document.getElementById('theme-icon');
        if(icon) {
            const isLight = document.documentElement.classList.contains('light-mode');
            icon.innerText = isLight ? '☀️' : '🌙';
        }
    }
    document.addEventListener('DOMContentLoaded', updateIcon);
</script>
'''

# --- TEMPLATES ---
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nintendo Web Tracker</title>
    {{ css|safe }}
</head>
<body class="section-sw2">
    <div class="main-header">
        <h1>🔐 Acceso Restringido</h1>
    </div>
    <div class="login-container">
        <h2>Identifícate</h2>
        {% if error %}<p class="error-msg">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" class="login-input" placeholder="Usuario" required>
            <input type="password" name="password" class="login-input" placeholder="Contraseña" required>
            <button type="submit" class="login-btn">Ingresar</button>
        </form>
        <br>
        <a href="/" style="color: var(--text-color); text-decoration: none; opacity: 0.7;">⬅ Volver a Pagina Principal</a>
    </div>
</body>
</html>
'''

LANDING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nintendo Web Tracker</title>
    {{ css|safe }}
</head>
<body class="section-sw2">
    <div class="main-header">
        <a href="/admin" class="admin-btn">⚙️ Admin</a>
        <button class="theme-toggle-btn" style="position:absolute; right:20px; top:20px; color:white;" onclick="toggleGlobalTheme()">
            <span id="theme-icon">🌙</span>
        </button>
        <h1>🎯 Nintendo Web Tracker</h1>
        <div class="gamer-subtitle">Pagina de Gamers para Gamers</div>
    </div>

    <div class="selection-container">
        <a href="/platform/switch1" class="option-card">
            <div class="option-img-container"><img src="{{ url_for('static', filename='switch1.png') }}"></div>
            <div class="option-title" style="color: #00b0ed;">Switch</div>
            <div class="last-update">🕒 {{ fechas['Switch 1'] }}</div>
        </a>
        <a href="/platform/switch2" class="option-card">
            <div class="option-img-container"><img src="{{ url_for('static', filename='switch2.png') }}"></div>
            <div class="option-title" style="color: #e60012;">Switch 2</div>
            <div class="last-update">🕒 {{ fechas['Switch 2'] }}</div>
        </a>
        <a href="/platform/ofertas" class="option-card">
            <div class="option-img-container"><img src="{{ url_for('static', filename='oferta.png') }}"></div>
            <div class="option-title" style="color: #ffae00;">🔥 OFERTAS</div>
            <div class="last-update">🕒 {{ fechas['Ofertas'] }}</div>
        </a>
        <a href="/platform/bestsellers" class="option-card">
            <div class="option-img-container"><img src="{{ url_for('static', filename='topsells.png') }}"></div>
            <div class="option-title" style="color: #8b0000;">🏆 Lo más Vendido</div>
            <div class="last-update">🕒 {{ fechas['Best Sellers'] }}</div>
        </a>
    </div>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nintendo Web Tracker</title>
    {{ css|safe }}
    <script>
        function iniciarActualizacion(plataforma) {
            const limit = document.getElementById('limit').value;
            document.getElementById('progress-container').style.display = 'block';
            fetch('/run_update', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `platform=${plataforma}&limit=${limit}`
            });
            const interval = setInterval(() => {
                fetch('/progress').then(r => r.json()).then(d => {
                    document.getElementById('progress-fill').style.width = d.percent + '%';
                    document.getElementById('status-msg').innerText = d.status;
                    document.getElementById('percent-msg').innerText = d.percent + '%';
                    if (!d.running && d.percent >= 100) {
                        clearInterval(interval);
                        alert("¡Completado!");
                        setTimeout(() => location.reload(), 1000);
                    }
                });
            }, 1000);
        }
    </script>
</head>
<body class="section-sw2">
    <div class="main-header" style="background: #333;">
        <a href="/" class="admin-btn">⬅ Volver al Inicio</a>
        <a href="/logout" class="admin-btn" style="left: auto; right: 20px; background: #ff4d4d;">Cerrar Sesión</a>
        <h1>⚙️ Panel Administrador</h1>
    </div>
    <div class="admin-panel">
        <div class="form-group">
            <label>📦 Cantidad a escanear:</label>
            <select id="limit">
                <option value="50">50 Juegos (Recomendado)</option>
                {% for n in range(100, 1050, 50) %}
                <option value="{{ n }}">{{ n }} Juegos</option>
                {% endfor %}
            </select>
        </div>
        
        <div style="display: grid; gap: 10px;">
            <button onclick="iniciarActualizacion('Switch 1')" class="btn-update" style="background: #00b0ed;">Actualizar Switch 1</button>
            <button onclick="iniciarActualizacion('Switch 2')" class="btn-update" style="background: #e60012;">Actualizar Switch 2</button>
            <button onclick="iniciarActualizacion('Ofertas')" class="btn-update" style="background: #ffae00; color: black;">🔥 Actualizar OFERTAS</button>
            <button onclick="iniciarActualizacion('Best Sellers')" class="btn-update" style="background: #8b0000; color: white;">🏆 Actualizar LO MÁS VENDIDO</button>
        </div>
        
        <div id="progress-container">
            <div style="display:flex; justify-content:space-between; color: white;">
                <span id="status-msg">Iniciando...</span>
                <span id="percent-msg">0%</span>
            </div>
            <div class="progress-bar-bg"><div id="progress-fill" class="progress-bar-fill"></div></div>
        </div>

        <h3 style="margin-top: 40px; text-align: left;">📊 Tiempo sin actualizar</h3>
        <table class="status-table">
            <thead>
                <tr>
                    <th>Plataforma</th>
                    <th>Última Actualización</th>
                    <th>Tiempo transcurrido</th>
                </tr>
            </thead>
            <tbody>
                {% for estado in db_status %}
                <tr class="{{ 'row-outdated' if estado.is_old else '' }}">
                    <td>{{ estado.plat }}</td>
                    <td>{{ estado.date }}</td>
                    <td>{{ estado.time_str }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

LIST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nintendo Web Tracker</title>
    {{ css|safe }}
    <style>
        .container-flex { display: flex; min-height: 100vh; }
        .sidebar { width: 300px; min-width: 300px; background: var(--sidebar-bg); padding: 25px; box-sizing: border-box; position: sticky; top: 0; height: 100vh; overflow-y: auto; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 20px; }
        .content { flex-grow: 1; padding: 30px; box-sizing: border-box; background: var(--bg-color); }
        .menu-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .menu-title { font-size: 1.8em; margin: 0; color: var(--accent); font-weight: 800; line-height: 1.1em; }
        .filter-group { background: rgba(0,0,0,0.05); padding: 15px; border-radius: 12px; border: 1px solid var(--border-color); }
        .filter-group label { display: block; margin-bottom: 8px; font-weight: bold; font-size: 0.9em; opacity: 0.9; cursor: pointer; }
        .control-row { display: flex; gap: 10px; }
        .control-col { flex: 1; }
        select, input[type="text"] { width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--input-bg); color: var(--text-color); font-size: 0.9em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
        
        .card { 
            background: var(--card-bg); border-radius: 12px; overflow: hidden; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: transform 0.2s; 
            text-decoration: none; color: inherit; display: block; border: 1px solid var(--border-color); 
            position: relative; display: flex; flex-direction: column;
        }
        .card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.2); border-color: var(--accent); }
        
        .sw2-banner { width: 100%; height: auto; display: block; border-bottom: 1px solid var(--border-color); }
        .card img.game-cover { width: 100%; height: 100%; object-fit: contain; background: #fff; border-bottom: 1px solid var(--border-color); }
        .info { padding: 12px; flex-grow: 1; }
        .title { font-size: 0.9em; font-weight: bold; height: 38px; overflow: hidden; margin-bottom: 5px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
        .price { font-size: 1.2em; color: var(--accent); font-weight: 800; }
        .pagination { display: flex; justify-content: center; gap: 10px; margin-top: 40px; align-items: center; }
        .page-btn { padding: 8px 20px; background: var(--accent); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .page-btn:disabled { background: #777; opacity: 0.5; cursor: not-allowed; }
        input[type="radio"], input[type="checkbox"] { transform: scale(1.2); margin-right: 8px; accent-color: var(--accent); }
        .back-link { display: inline-block; margin-bottom: 20px; color: var(--text-color); text-decoration: none; font-weight: bold; font-size: 0.9em; opacity: 0.7; }
        .back-link:hover { opacity: 1; }
    </style>
</head>
<body class="{{ section_class }}">

<div class="container-flex">
    <div class="sidebar">
        <a href="/" class="back-link">⬅ Volver al Inicio</a>
        <div class="menu-header-row">
            <h1 class="menu-title">{{ plataforma_titulo }}</h1>
            <button class="theme-toggle-btn" onclick="toggleGlobalTheme()">
                <span id="theme-icon">🌙</span>
            </button>
        </div>
        <div class="filter-group">
            <div class="control-row">
                <div class="control-col">
                    <label>Ordenar:</label>
                    <select id="sortOrder" onchange="aplicarFiltros()">
                        <option value="asc">- Precio</option>
                        <option value="desc">+ Precio</option>
                    </select>
                </div>
                <div class="control-col">
                    <label>Por pág:</label>
                    <select id="itemsPerPage" onchange="cambiarItemsPorPagina()">
                        <option value="20">20</option>
                        <option value="40">40</option>
                        <option value="60">60</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div class="filter-group">
            <label>Buscar juego:</label>
            <input type="text" id="searchInput" placeholder="Escribe el nombre..." oninput="aplicarFiltros()">
        </div>

        <div class="filter-group">
            <label style="margin-bottom:12px;">Rango de Precios:</label>
            <label><input type="radio" name="priceRange" value="all" checked onchange="aplicarFiltros()"> Todos</label>
            
            <label><input type="radio" name="priceRange" value="no-free" onchange="aplicarFiltros()"> Ocultar Gratis ($0)</label>
            <label><input type="radio" name="priceRange" value="1-20000" onchange="aplicarFiltros()"> $1 - $20k</label>
            
            <label><input type="radio" name="priceRange" value="20000-40000" onchange="aplicarFiltros()"> $20k - $40k</label>
            <label><input type="radio" name="priceRange" value="40000-60000" onchange="aplicarFiltros()"> $40k - $60k</label>
            <label><input type="radio" name="priceRange" value="60000-80000" onchange="aplicarFiltros()"> $60k - $80k</label>
            <label><input type="radio" name="priceRange" value="80000-100000" onchange="aplicarFiltros()"> $80k - $100k</label>
            <label><input type="radio" name="priceRange" value="100000-max" onchange="aplicarFiltros()"> + $100k</label>
        </div>
        
        <div style="margin-top: auto; font-size: 0.8em; opacity: 0.7; text-align: center;">
            Mostrando <span id="visibleCount">0</span> de <span id="totalCount">0</span> juegos
        </div>
    </div>
    <div class="content">
        <div id="gamesGrid" class="grid"></div>
        <div class="pagination">
            <button id="btnPrev" class="page-btn" onclick="cambiarPagina(-1)">Anterior</button>
            <span id="pageIndicator" style="font-weight:bold; opacity:0.8;">Página 1</span>
            <button id="btnNext" class="page-btn" onclick="cambiarPagina(1)">Siguiente</button>
        </div>
    </div>
</div>

<script>
    const rawData = {{ juegos_json|safe }};
    let juegosFiltrados = [];
    let paginaActual = 1;
    let itemsPorPagina = 20;

    document.addEventListener('DOMContentLoaded', () => {
        aplicarFiltros();
    });

    function aplicarFiltros() {
        const sortOrder = document.getElementById('sortOrder').value;
        const priceRange = document.querySelector('input[name="priceRange"]:checked').value;
        const searchText = document.getElementById('searchInput').value.toLowerCase();

        juegosFiltrados = rawData.filter(juego => {
            const precio = juego.precio;
            
            if (searchText && !juego.titulo.toLowerCase().includes(searchText)) return false;

            if (priceRange === 'no-free') {
                if (precio <= 0) return false; 
            } else if (priceRange === '1-20000') {
                if (precio < 1 || precio > 20000) return false;
            } else if (priceRange !== 'all') {
                const parts = priceRange.split('-');
                const min = parseInt(parts[0]);
                if (parts[1] === 'max') { if (precio < min) return false; } 
                else { if (precio < min || precio > parseInt(parts[1])) return false; }
            }
            return true;
        });
        juegosFiltrados.sort((a, b) => sortOrder === 'asc' ? a.precio - b.precio : b.precio - a.precio);
        paginaActual = 1;
        document.getElementById('totalCount').innerText = rawData.length;
        document.getElementById('visibleCount').innerText = juegosFiltrados.length;
        renderizarGrid();
    }

    function cambiarItemsPorPagina() {
        itemsPorPagina = parseInt(document.getElementById('itemsPerPage').value);
        paginaActual = 1;
        renderizarGrid();
    }

    function cambiarPagina(delta) {
        const maxPages = Math.ceil(juegosFiltrados.length / itemsPorPagina);
        const nueva = paginaActual + delta;
        if (nueva >= 1 && nueva <= maxPages) {
            paginaActual = nueva;
            renderizarGrid();
            document.querySelector('.content').scrollTo({top:0, behavior:'smooth'});
        }
    }

    function renderizarGrid() {
        const grid = document.getElementById('gamesGrid');
        grid.innerHTML = '';
        const start = (paginaActual - 1) * itemsPorPagina;
        const end = start + itemsPorPagina;
        const pageItems = juegosFiltrados.slice(start, end);

        if (pageItems.length === 0) {
            grid.innerHTML = '<h3 style="opacity:0.6;">No hay resultados con estos filtros.</h3>';
            document.getElementById('pageIndicator').innerText = '0 / 0';
            return;
        }

        pageItems.forEach(j => {
            const precioFmt = j.precio.toLocaleString('es-AR', {style: 'currency', currency: 'ARS'});
            
            let bannerHTML = '';
            if(j.plataforma === 'Switch 2') {
                bannerHTML = `<img src="/static/bannersw2.jpg" class="sw2-banner">`;
            }

            grid.innerHTML += `
                <a href="${j.url}" target="_blank" class="card" title="Ver en eShop">
                    ${bannerHTML}
                    <img src="${j.imagen}" loading="lazy" class="game-cover">
                    <div class="info">
                        <div class="title">${j.titulo}</div>
                        <div class="price">${precioFmt}</div>
                    </div>
                </a>
            `;
        });
        const maxPages = Math.ceil(juegosFiltrados.length / itemsPorPagina);
        document.getElementById('pageIndicator').innerText = `Página ${paginaActual} de ${maxPages}`;
        document.getElementById('btnPrev').disabled = paginaActual === 1;
        document.getElementById('btnNext').disabled = paginaActual === maxPages;
    }
</script>
</body>
</html>
'''

# --- BACKEND ---
class NintendoManager:
    def __init__(self, db_name="nintendo_vault.db"):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS juegos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, plataforma TEXT, precio_lista REAL, imagen_url TEXT, url_producto TEXT, fecha_registro DATETIME, UNIQUE(titulo, plataforma))''')
            conn.commit()

    def guardar_datos(self, lista_juegos):
        nuevos = 0
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            for juego in lista_juegos:
                cursor.execute('''INSERT OR IGNORE INTO juegos (titulo, plataforma, precio_lista, imagen_url, url_producto, fecha_registro) VALUES (?, ?, ?, ?, ?, ?)''', (juego['titulo'], juego['plataforma'], juego['precio_lista'], juego['imagen'], juego['url'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                if cursor.rowcount > 0: nuevos += 1
            conn.commit()
        return nuevos

    def obtener_fechas_actualizacion(self):
        fechas = {"Switch 1": "--", "Switch 2": "--", "Ofertas": "--", "Best Sellers": "--"}
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            for plat in fechas.keys():
                cursor.execute("SELECT MAX(fecha_registro) FROM juegos WHERE plataforma = ?", (plat,))
                res = cursor.fetchone()
                if res and res[0]:
                    try: fechas[plat] = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    except: pass
        return fechas

    def obtener_estado_bases(self):
        estado = []
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            for plat in ["Switch 1", "Switch 2", "Ofertas", "Best Sellers"]:
                cursor.execute("SELECT MAX(fecha_registro) FROM juegos WHERE plataforma = ?", (plat,))
                res = cursor.fetchone()
                
                time_str = "--"
                is_old = False
                
                if res and res[0]:
                    try:
                        last_update = datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
                        diff = datetime.now() - last_update
                        total_seconds = diff.total_seconds()
                        hours = int(total_seconds // 3600)
                        minutes = int((total_seconds % 3600) // 60)
                        time_str = f"{hours}h {minutes}m"
                        if diff.days > 7: is_old = True
                    except: pass
                
                estado.append({'plat': plat, 'date': res[0] if res else '--', 'time_str': time_str, 'is_old': is_old})
        return estado

class NintendoScraper:
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless') 
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1280,800')
        self.options.add_argument("user-agent=Mozilla/5.0")
        
        chrome_bin = os.environ.get("GOOGLE_CHROME_BIN")
        if chrome_bin:
            self.options.binary_location = chrome_bin

        self.driver = webdriver.Chrome(options=self.options)

    def scrape_custom(self, plataforma, limite):
        global TASK_STATUS
        
        if plataforma == "Switch 1":
            url = "https://www.nintendo.com/es-ar/store/games/#show=0&p=1&sort=df&f=corePlatforms&corePlatforms=Nintendo+Switch"
        elif plataforma == "Switch 2":
            url = "https://www.nintendo.com/es-ar/store/games/#show=0&p=1&sort=df&f=corePlatforms&corePlatforms=Nintendo+Switch+2"
        elif plataforma == "Ofertas":
            url = "https://www.nintendo.com/es-ar/store/games/#show=0&p=1&sort=df&f=topLevelFilters&topLevelFilters=Ofertas"
        else: # Best Sellers
            url = "https://www.nintendo.com/es-ar/store/games/best-sellers/#sort=df&p=0"
        
        TASK_STATUS['status'] = f"Conectando a {plataforma}..."
        TASK_STATUS['percent'] = 5
        self.driver.get(url)
        time.sleep(3)

        TASK_STATUS['status'] = f"Cargando juegos (Meta: {limite})..."
        while True:
            items = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/store/products/')]")
            count = len(items)
            progreso = min(50, int((count/limite)*50))
            TASK_STATUS['percent'] = 5 + progreso
            
            if count >= limite: break
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Cargar más') or contains(., 'Load more')]")
                if btn.is_displayed():
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                else: break
            except: 
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(1)
                if len(self.driver.find_elements(By.XPATH, "//a[contains(@href, '/store/products/')]")) == count: break

        items = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/store/products/')]")[:limite]
        res = []
        total = len(items)
        for i, item in enumerate(items):
            proc_prog = int((i/total)*50)
            TASK_STATUS['percent'] = 50 + proc_prog
            TASK_STATUS['status'] = f"Procesando {i}/{total}..."
            try:
                url_prod = item.get_attribute('href')
                txt = item.text.split('\n')
                if len(txt) < 2: continue
                title = txt[0]
                price = 0.0
                for l in txt:
                    if '$' in l:
                        try: price = float(l.replace('$', '').replace('.', '').replace(',', '.').strip())
                        except: pass
                        break
                try: img = item.find_element(By.TAG_NAME, "img").get_attribute("src")
                except: img = ""
                res.append({"titulo": title, "plataforma": plataforma, "precio_lista": price, "imagen": img, "url": url_prod})
            except: continue
            
        self.driver.quit()
        return res

def worker(plat, lim):
    global TASK_STATUS
    TASK_STATUS['running'] = True
    try:
        data = NintendoScraper().scrape_custom(plat, lim)
        TASK_STATUS['status'] = "Guardando en DB..."
        TASK_STATUS['percent'] = 98
        added = NintendoManager().guardar_datos(data)
        TASK_STATUS['status'] = f"Listo. {added} nuevos guardados en '{plat}'."
        TASK_STATUS['percent'] = 100
    except Exception as e:
        TASK_STATUS['status'] = f"Error: {e}"
    finally:
        TASK_STATUS['running'] = False

# --- ROUTES ---

@app.route('/')
def landing(): return render_template_string(LANDING_TEMPLATE, css=COMMON_CSS, fechas=NintendoManager().obtener_fechas_actualizacion())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = "Credenciales incorrectas"
    return render_template_string(LOGIN_TEMPLATE, css=COMMON_CSS, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('landing'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    db_status = NintendoManager().obtener_estado_bases()
    return render_template_string(ADMIN_TEMPLATE, css=COMMON_CSS, db_status=db_status)

@app.route('/run_update', methods=['POST'])
def run_update():
    if not session.get('logged_in'): return jsonify({'status': 'error', 'msg': 'Unauthorized'}), 403
    if TASK_STATUS['running']: return jsonify({'status': 'busy'})
    threading.Thread(target=worker, args=(request.form.get('platform'), int(request.form.get('limit')))).start()
    return jsonify({'status': 'ok'})

@app.route('/progress')
def progress(): return jsonify(TASK_STATUS)

@app.route('/platform/<ptype>')
def view(ptype):
    if ptype == 'switch1': plat, section = "Switch 1", "section-sw1"
    elif ptype == 'switch2': plat, section = "Switch 2", "section-sw2"
    elif ptype == 'ofertas': plat, section = "Ofertas", "section-offers"
    else: plat, section = "Best Sellers", "section-bestsellers"
    
    with sqlite3.connect("nintendo_vault.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT titulo, precio_lista, imagen_url, url_producto, plataforma FROM juegos WHERE plataforma = ?", (plat,))
        rows = cursor.fetchall()
    
    juegos_lista = [{"titulo": r[0], "precio": r[1], "imagen": r[2], "url": r[3], "plataforma": r[4]} for r in rows]
    return render_template_string(LIST_TEMPLATE, juegos_json=json.dumps(juegos_lista), plataforma_titulo=plat, css=COMMON_CSS, section_class=section)

if __name__ == "__main__":
    NintendoManager()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)