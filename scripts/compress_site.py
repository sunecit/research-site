from pathlib import Path
from time import perf_counter
from statistics import median
import gzip
import hashlib
import json
import platform
import zlib

VERSION = "v1.1"
LEVEL = 9
REPEATS = 11

project = Path(__file__).resolve().parent.parent
source = project / "experiments/input/site-snapshot.tar"
output = project / "experiments/results"
output.mkdir(parents=True, exist_ok=True)

data = source.read_bytes()

# Предварительный запуск не включаем в измерения.
gzip.compress(data, compresslevel=LEVEL, mtime=0)

times = []

for _ in range(REPEATS):
    start = perf_counter()
    compressed = gzip.compress(data, compresslevel=LEVEL, mtime=0)
    times.append(perf_counter() - start)

# Проверяем сжатие без потери данных.
if gzip.decompress(compressed) != data:
    raise RuntimeError("Распакованные данные отличаются от исходных.")

median_ms = median(times) * 1000
reduction = (1 - len(compressed) / len(data)) * 100

result = {
    "version": VERSION,
    "gzip_level": LEVEL,
    "repeats": REPEATS,
    "input_sha256": hashlib.sha256(data).hexdigest(),
    "input_bytes": len(data),
    "compressed_bytes": len(compressed),
    "reduction_percent": reduction,
    "times_ms": [value * 1000 for value in times],
    "median_ms": median_ms,
    "roundtrip_ok": True,
    "python": platform.python_version(),
    "zlib": zlib.ZLIB_RUNTIME_VERSION,
    "platform": platform.platform(),
}

(output / f"{VERSION}.tar.gz").write_bytes(compressed)
(output / f"{VERSION}.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(f"Версия: {VERSION}")
print(f"Уровень gzip: {LEVEL}")
print(f"Количество измерений: {REPEATS}")
print(f"Исходный размер: {len(data)} байт")
print(f"Размер после сжатия: {len(compressed)} байт")
print(f"Уменьшение размера: {reduction:.2f}%")
print(f"Медиана времени сжатия: {median_ms:.3f} мс")
print("Проверка восстановления данных: успешно")
print(f"Результаты сохранены: experiments/results/{VERSION}.json")
