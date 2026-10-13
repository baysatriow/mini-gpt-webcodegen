"""Read-only NVIDIA telemetry for actual training and throughput experiments."""
import json
import statistics
import subprocess
import threading
import time
from pathlib import Path


class GpuMonitor:
    fields = ('utilization_pct', 'memory_used_mib', 'power_w', 'temperature_c', 'sm_clock_mhz')

    def __init__(self, path, interval=0.5):
        self.path, self.interval = Path(path), interval
        self.samples, self.errors = [], []
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.path.exists():
            raise ValueError('Telemetry output already exists')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return self

    def _loop(self):
        with self.path.open('x', encoding='utf-8') as handle:
            while not self.stop_event.is_set():
                try:
                    output = subprocess.check_output(['nvidia-smi', '-i', '0',
                        '--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu,clocks.current.sm',
                        '--format=csv,noheader,nounits'], text=True, timeout=5)
                    values = [float(v.strip()) for v in output.strip().split(',')]
                    sample = {'time_unix': time.time(), **dict(zip(self.fields, values))}
                    self.samples.append(sample)
                    handle.write(json.dumps(sample) + '\n')
                    handle.flush()
                except Exception as error:
                    self.errors.append(str(error))
                self.stop_event.wait(self.interval)

    def finish(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=6)
        result = {'sample_count': len(self.samples), 'interval_seconds': self.interval,
                  'raw_path': str(self.path), 'errors': self.errors,
                  'memory_scope': 'nvidia-smi memory includes other desktop applications'}
        for field in self.fields:
            values = [s[field] for s in self.samples]
            result[field] = {'mean': statistics.mean(values) if values else None,
                             'max': max(values) if values else None,
                             'min': min(values) if values else None}
        return result
