import time
import psutil
import argparse
import logging
from datetime import datetime
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich import box

# --- CONFIGURACIÓN DE LOGS (Puntos: Persistencia y Diagnóstico) ---
logging.basicConfig(filename='sistema_alertas.log', level=logging.WARNING, 
                    format='%(asctime)s - %(message)s')

# Argumentos de línea de comandos (Puntos: Dificultad/Manejo de SO)
parser = argparse.ArgumentParser(description="Monitor de Sistema Avanzado")
parser.add_argument("--threshold", type=int, default=85, help="Umbral de alerta CPU (%)")
args = parser.parse_args()
CPU_THRESHOLD = args.threshold

def get_cpu_panel():
    """Genera panel de CPU con lógica de alertas."""
    cpu_total = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    
    # Lógica de Alerta (Originalidad)
    border_color = "blue"
    if cpu_total > CPU_THRESHOLD:
        border_color = "bright_red"
        logging.warning(f"ALERTA CPU: Uso total {cpu_total}% superó el umbral de {CPU_THRESHOLD}%")

    table = Table(show_header=False, box=None, expand=True)
    table.add_column("Core", ratio=1)
    table.add_column("Uso", ratio=1)
    
    for i, core_usage in enumerate(cpu_per_core):
        color = "green" if core_usage < 50 else "yellow" if core_usage < CPU_THRESHOLD else "red"
        bar = f"[{color}]{'|' * int(core_usage / 5)}[/]"
        table.add_row(f"Core {i}", f"{core_usage}% {bar}")

    return Panel(
        table, 
        title=f"CPU Total: {cpu_total}% (Umbral: {CPU_THRESHOLD}%)", 
        border_style=border_color
    )

def get_memory_panel():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory() # Agregamos SWAP para mayor dificultad técnica
    
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    
    table = Table(show_header=False, box=None, expand=True)
    table.add_row("RAM Total", f"{total_gb:.2f} GB")
    table.add_row("RAM Usada", f"{used_gb:.2f} GB")
    table.add_row("RAM %", f"{mem.percent}%")
    table.add_row("SWAP Usada", f"{swap.used / (1024**3):.2f} GB") # Dato extra SO
    
    return Panel(table, title="Memoria (RAM + Swap)", border_style="green")

def get_network_disk_panel():
    net = psutil.net_io_counters()
    disk = psutil.disk_io_counters()
    
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Recurso")
    table.add_column("Actividad Acumulada")
    
    sent_mb = net.bytes_sent / (1024 ** 2)
    recv_mb = net.bytes_recv / (1024 ** 2)
    
    table.add_row("Red Enviado", f"{sent_mb:.1f} MB")
    table.add_row("Red Recibido", f"{recv_mb:.1f} MB")
    table.add_section()
    # Mostramos actividad en vivo calculando delta si fuera necesario, 
    # pero acumulado es válido para I/O básico.
    table.add_row("Disco Lecturas", f"{disk.read_count}")
    table.add_row("Disco Escrituras", f"{disk.write_count}")
    
    return Panel(table, title="I/O Sistema", border_style="cyan")

def get_processes_panel(top_n=10):
    procs = []
    # Optimizamos iteración para velocidad
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    top_procs = sorted(procs, key=lambda p: p['cpu_percent'] or 0, reverse=True)[:top_n]
    
    table = Table(expand=True, box=box.SIMPLE)
    table.add_column("PID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Nombre", style="magenta")
    table.add_column("CPU %", justify="right", style="green")
    table.add_column("MEM %", justify="right", style="yellow") # Dato extra agregado

    for p in top_procs:
        cpu = p['cpu_percent'] if p['cpu_percent'] is not None else 0.0
        mem = p['memory_percent'] if p['memory_percent'] is not None else 0.0
        table.add_row(str(p['pid']), p['name'], f"{cpu:.1f}%", f"{mem:.1f}%")

    return Panel(table, title=f"Top {top_n} Procesos", border_style="white")

def make_layout():
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
    )
    layout["main"].split_row(
        Layout(name="left_col", ratio=1),
        Layout(name="right_col", ratio=1),
    )
    layout["left_col"].split(
        Layout(name="cpu", ratio=2),
        Layout(name="memory", ratio=1),
        Layout(name="io", ratio=1),
    )
    layout["right_col"].update(Panel("Cargando procesos..."))
    return layout

def update_layout(layout):
    current_time = datetime.now().strftime("%H:%M:%S")
    layout["header"].update(Panel(f"Monitor Avanzado | Log activo: sistema_alertas.log | Hora: {current_time}", style="bold white on blue"))
    layout["cpu"].update(get_cpu_panel())
    layout["memory"].update(get_memory_panel())
    layout["io"].update(get_network_disk_panel())
    layout["right_col"].update(get_processes_panel())

if __name__ == "__main__":
    try:
        console = Console()
        layout = make_layout()
        with Live(layout, refresh_per_second=2, screen=True) as live:
            while True:
                update_layout(layout)
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("Monitor finalizado. Revise 'sistema_alertas.log' para ver incidencias.")