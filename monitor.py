import time
import psutil
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich import box
from datetime import datetime

# Configuración
UPDATE_INTERVAL = 0.5  # Segundos

def get_cpu_panel():
    """Genera el panel de información de CPU."""
    # Uso total y por núcleo
    cpu_total = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    
    # Crear tabla para los núcleos
    table = Table(show_header=False, box=None, expand=True)
    table.add_column("Core", ratio=1)
    table.add_column("Uso", ratio=1)
    
    # Formato visual de barras para cada núcleo
    for i, core_usage in enumerate(cpu_per_core):
        color = "green" if core_usage < 50 else "yellow" if core_usage < 80 else "red"
        bar = f"[{color}]{'|' * int(core_usage / 5)}[/]"
        table.add_row(f"Core {i}", f"{core_usage}% {bar}")

    return Panel(
        table, 
        title=f"CPU Total: {cpu_total}%", 
        border_style="blue"
    )

def get_memory_panel():
    """Genera el panel de Memoria RAM."""
    mem = psutil.virtual_memory()
    
    # Convertir bytes a GB
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    
    table = Table(show_header=False, box=None, expand=True)
    table.add_row("Total", f"{total_gb:.2f} GB")
    table.add_row("Usada", f"{used_gb:.2f} GB")
    table.add_row("Porcentaje", f"{mem.percent}%")
    
    color = "green" if mem.percent < 60 else "yellow" if mem.percent < 85 else "red"
    
    return Panel(
        table, 
        title=f"[b]Memoria RAM[/b]", 
        border_style=color
    )

def get_network_disk_panel():
    """Genera panel combinado de Red y Disco (Acumulados)."""
    net = psutil.net_io_counters()
    disk = psutil.disk_io_counters()
    
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Métrica")
    table.add_column("Valor")
    
    # Red (convertimos a MB para leer mejor)
    sent_mb = net.bytes_sent / (1024 ** 2)
    recv_mb = net.bytes_recv / (1024 ** 2)
    
    table.add_row("Red Enviado", f"{sent_mb:.1f} MB")
    table.add_row("Red Recibido", f"{recv_mb:.1f} MB")
    table.add_section()
    table.add_row("Disco Lecturas", f"{disk.read_count}")
    table.add_row("Disco Escrituras", f"{disk.write_count}")
    
    return Panel(table, title="I/O Sistema", border_style="cyan")

def get_processes_panel(top_n=10):
    """Genera tabla con el Top N de procesos por CPU."""
    # Obtenemos procesos. Iterar es más rápido que pedir una lista completa.
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            # cpu_percent puede devolver 0.0 la primera vez si no se espera,
            # pero en un loop continuo funciona bien.
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    # Ordenar por uso de CPU descendente
    top_procs = sorted(procs, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:top_n]
    
    table = Table(expand=True, box=box.SIMPLE)
    table.add_column("PID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Nombre", style="magenta")
    table.add_column("CPU %", justify="right", style="green")

    for p in top_procs:
        cpu = p['cpu_percent'] if p['cpu_percent'] is not None else 0.0
        table.add_row(str(p['pid']), p['name'], f"{cpu:.1f}%")

    return Panel(table, title=f"Top {top_n} Procesos (CPU)", border_style="white")

def make_layout():
    """Define la estructura de la interfaz."""
    layout = Layout(name="root")
    
    # Dividimos: Cabecera (arriba), Cuerpo (medio), Pie (abajo)
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
    )
    
    # Dividimos el cuerpo principal en dos columnas
    layout["main"].split_row(
        Layout(name="left_col", ratio=1),
        Layout(name="right_col", ratio=1),
    )
    
    # Columna izquierda: CPU arriba, Memoria y Disco/Red abajo
    layout["left_col"].split(
        Layout(name="cpu", ratio=2),
        Layout(name="memory", ratio=1),
        Layout(name="io", ratio=1),
    )
    
    # Columna derecha: Solo procesos
    layout["right_col"].update(Panel("Cargando procesos..."))
    
    return layout

def update_layout(layout):
    """Actualiza los datos dentro del layout."""
    # Cabecera con la hora
    current_time = datetime.now().strftime("%H:%M:%S")
    layout["header"].update(Panel(f"Monitor de Sistema - {current_time}", style="bold white on blue"))
    
    # Actualizar paneles
    layout["cpu"].update(get_cpu_panel())
    layout["memory"].update(get_memory_panel())
    layout["io"].update(get_network_disk_panel())
    layout["right_col"].update(get_processes_panel())

def main():
    console = Console()
    layout = make_layout()
    
    # Context Manager 'Live' maneja el refresco sin parpadeos
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            update_layout(layout)
            time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Monitor detenido.")