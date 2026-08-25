"""Подготовка звуков манула из исходной записи.

Я не слышу файл, поэтому работаю по цифрам: смотрю на огибающую громкости,
нахожу участки со звуком, вырезаю их, свожу в моно, при необходимости чищу от
ровного фонового шума и нормализую. Minecraft хочет моно OGG Vorbis — иначе не
работает затухание по расстоянию.

Команды:
  analyze <файл>                     обзор: параметры, огибающая по 0.25 с, участки со звуком
  zoom <файл> <от> <до>              та же огибающая, но по 20 мс — чтобы найти точные границы
  noise <файл> <от> <до>             спектр фонового шума на участке (проверить, что там тишина)
  cut <файл> <от> <до> <выход.ogg>   вырезать, свести в моно, нормализовать, записать
       [--denoise <от> <до>]         вычесть спектр шума, взятый с указанного участка
       [--highpass <Гц>]             срезать низкочастотный гул
       [--gain <dBFS>]               целевой пик, по умолчанию -1.0
       [--fixed-gain <dB>]           вместо нормализации — заданное усиление
       [--fade <мс>]                 фейд на входе и выходе, по умолчанию 20
"""
import sys

import numpy as np
import soundfile as sf

HOP_MS = 20
MERGE_GAP_MS = 250
MIN_EVENT_MS = 120
THRESH_FRAC = 0.06

FFT_SIZE = 1024
FFT_HOP = 256


def db(x):
    return -np.inf if x <= 0 else 20.0 * np.log10(x)


def load_mono(path):
    data, rate = sf.read(path, always_2d=True, dtype="float32")
    return data.mean(axis=1).astype(np.float64), rate, data


def envelope(mono, rate, hop_ms=HOP_MS):
    hop = max(1, int(rate * hop_ms / 1000))
    n = len(mono) // hop
    frames = mono[:n * hop].reshape(n, hop)
    return np.sqrt((frames ** 2).mean(axis=1)), hop


def print_envelope(mono, rate, per_line_s, t_offset=0.0):
    rms, hop = envelope(mono, rate)
    if not len(rms):
        print("  (участок короче одного окна)")
        return
    per_line = max(1, int(per_line_s * rate / hop))
    peak_rms = rms.max()
    for i in range(0, len(rms), per_line):
        chunk = rms[i:i + per_line]
        level = chunk.max() / peak_rms if peak_rms else 0
        t = t_offset + i * hop / rate
        bar = "#" * int(round(level * 56))
        print(f"  {t:6.2f}s |{bar:<56}| {db(float(chunk.max())):6.1f} dB")


def find_events(rms, hop, rate):
    peak = rms.max()
    if peak <= 0:
        return []
    loud = rms > peak * THRESH_FRAC
    events, start = [], None
    for i, is_loud in enumerate(loud):
        if is_loud and start is None:
            start = i
        elif not is_loud and start is not None:
            events.append([start, i])
            start = None
    if start is not None:
        events.append([start, len(loud)])

    frames_per_ms = rate / hop / 1000
    merged = []
    for ev in events:
        if merged and ev[0] - merged[-1][1] <= MERGE_GAP_MS * frames_per_ms:
            merged[-1][1] = ev[1]
        else:
            merged.append(ev)
    return [e for e in merged if e[1] - e[0] >= MIN_EVENT_MS * frames_per_ms]


def stft(x):
    win = np.hanning(FFT_SIZE)
    n = 1 + max(0, (len(x) - FFT_SIZE)) // FFT_HOP
    frames = np.stack([x[i * FFT_HOP:i * FFT_HOP + FFT_SIZE] * win for i in range(n)])
    return np.fft.rfft(frames, axis=1)


def istft(spec, length):
    win = np.hanning(FFT_SIZE)
    frames = np.fft.irfft(spec, axis=1) * win
    out = np.zeros(length + FFT_SIZE)
    norm = np.zeros(length + FFT_SIZE)
    for i, frame in enumerate(frames):
        a = i * FFT_HOP
        out[a:a + FFT_SIZE] += frame
        norm[a:a + FFT_SIZE] += win ** 2
    # Порог относительный: где окна почти не перекрываются, norm близка к нулю и
    # деление на неё раздувает погрешность в щелчок. Такие края всё равно
    # отрезаются вместе с дополнением в denoise().
    norm = np.maximum(norm, 1e-3 * norm.max())
    return (out / norm)[:length]


def denoise(seg, noise, alpha=1.6, floor=0.08):
    """Спектральное вычитание: убираем усреднённый спектр шума.

    floor не даёт вычесть всё до нуля — иначе вместо шума появляются булькающие
    артефакты («musical noise»), которые слышны хуже самого шума.

    Сигнал дополняется нулями на длину окна с обеих сторон: только так каждый
    сэмпл исходника попадает под полное перекрытие окон и восстанавливается без
    краевых выбросов.
    """
    if len(noise) < FFT_SIZE:
        raise SystemExit("участок шума короче окна FFT — возьми подольше")
    noise_mag = np.abs(stft(noise)).mean(axis=0)

    pad = FFT_SIZE
    padded = np.concatenate([np.zeros(pad), seg, np.zeros(pad)])
    spec = stft(padded)
    mag = np.abs(spec)
    phase = spec / np.maximum(mag, 1e-12)
    cleaned = np.maximum(mag - alpha * noise_mag, floor * mag)
    return istft(cleaned * phase, len(padded))[pad:pad + len(seg)]


def highpass(x, rate, cutoff, q=0.7071):
    """Биквад-фильтр высоких частот (RBJ cookbook), 2-й порядок.

    Фон в записи — низкочастотный гул, а голос манула лежит выше, поэтому срез
    на ~150 Гц убирает шум почти не задевая сам крик.
    """
    w0 = 2 * np.pi * cutoff / rate
    cos_w0, alpha = np.cos(w0), np.sin(w0) / (2 * q)
    b0, b1, b2 = (1 + cos_w0) / 2, -(1 + cos_w0), (1 + cos_w0) / 2
    a0, a1, a2 = 1 + alpha, -2 * cos_w0, 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    out = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[i] = yi
        x2, x1 = x1, xi
        y2, y1 = y1, yi
    return out


def apply_fade(x, rate, fade_ms):
    n = min(int(rate * fade_ms / 1000), len(x) // 2)
    if n <= 0:
        return x
    ramp = np.linspace(0.0, 1.0, n)
    x = x.copy()
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    return x


def cmd_analyze(path):
    mono, rate, raw = load_mono(path)
    print(f"файл          : {path}")
    print(f"каналов       : {raw.shape[1]}, частота {rate} Гц, длительность {len(mono) / rate:.2f} с")
    if raw.shape[1] == 2:
        diff = float(np.abs(raw[:, 0] - raw[:, 1]).max())
        note = " (каналы практически идентичны — стерео фиктивное)" if diff < 0.01 else ""
        print(f"разница L/R   : {diff:.4f}{note}")
    peak = float(np.abs(mono).max())
    print(f"пик (моно)    : {peak:.4f} = {db(peak):.1f} dBFS")
    print(f"DC-смещение   : {float(mono.mean()):+.5f}")
    print(f"клиппинг      : {int((np.abs(mono) >= 0.999).sum())} сэмплов")
    print("\nОгибающая (строка = 0.25 с):")
    print_envelope(mono, rate, 0.25)
    rms, hop = envelope(mono, rate)
    events = find_events(rms, hop, rate)
    print(f"\nУчастков со звуком: {len(events)}")
    for n, (a, b) in enumerate(events, 1):
        t0, t1 = a * hop / rate, b * hop / rate
        seg_peak = float(np.abs(mono[a * hop:b * hop]).max())
        print(f"{n:>3} {t0:>7.2f}s {t1:>7.2f}s  длина {t1 - t0:>5.2f}s  пик {db(seg_peak):>6.1f} dB")


def cmd_zoom(path, t0, t1):
    mono, rate, _ = load_mono(path)
    a, b = int(t0 * rate), int(t1 * rate)
    seg = mono[a:b]
    print(f"{path}  {t0:.2f}–{t1:.2f} с, окно 20 мс, пик участка {db(float(np.abs(seg).max())):.1f} dBFS")
    print_envelope(seg, rate, HOP_MS / 1000, t_offset=t0)


def cmd_noise(path, t0, t1):
    mono, rate, _ = load_mono(path)
    seg = mono[int(t0 * rate):int(t1 * rate)]
    rms = float(np.sqrt((seg ** 2).mean()))
    print(f"участок {t0:.2f}–{t1:.2f} с: RMS {db(rms):.1f} dB, пик {db(float(np.abs(seg).max())):.1f} dBFS")
    mag = np.abs(stft(seg)).mean(axis=0)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1 / rate)
    print("спектр по полосам:")
    for lo, hi in [(0, 30), (30, 60), (60, 90), (90, 130), (130, 200), (200, 300),
                   (300, 500), (500, 1000), (1000, 2000), (2000, 4000),
                   (4000, 8000), (8000, 16000)]:
        band = mag[(freqs >= lo) & (freqs < hi)]
        if len(band):
            print(f"  {lo:>6}–{hi:<6.0f} Гц : {db(float(band.mean())):>6.1f} dB")


def cmd_cut(path, t0, t1, out, noise_range, target_db, fade_ms, hp_hz, fixed_gain):
    mono, rate, _ = load_mono(path)
    seg = mono[int(t0 * rate):int(t1 * rate)]
    if not len(seg):
        raise SystemExit("пустой участок")
    print(f"вырезано      : {t0:.2f}–{t1:.2f} с ({len(seg) / rate:.2f} с), пик {db(float(np.abs(seg).max())):.1f} dBFS")

    noise = None
    if noise_range:
        n0, n1 = noise_range
        noise = mono[int(n0 * rate):int(n1 * rate)]

    if hp_hz:
        before = float(np.sqrt((seg ** 2).mean()))
        seg = highpass(seg, rate, hp_hz)
        if noise is not None:
            noise = highpass(noise, rate, hp_hz)
        print(f"ФВЧ {hp_hz:.0f} Гц    : RMS {db(before):.1f} → {db(float(np.sqrt((seg ** 2).mean()))):.1f} dB")

    if noise is not None:
        before = float(np.sqrt((seg ** 2).mean()))
        seg = denoise(seg, noise)
        n0, n1 = noise_range
        print(f"шумодав       : профиль {n0:.2f}–{n1:.2f} с, "
              f"RMS {db(before):.1f} → {db(float(np.sqrt((seg ** 2).mean()))):.1f} dB")

    seg = apply_fade(seg, rate, fade_ms)

    peak = float(np.abs(seg).max())
    if fixed_gain is not None:
        # Фиксированное усиление нужно, чтобы прогнать участок чистого шума
        # ровно с тем же коэффициентом, что достался крику, и увидеть, на каком
        # уровне фон останется в готовом файле.
        seg = seg * 10 ** (fixed_gain / 20)
        print(f"усиление      : {fixed_gain:+.1f} dB (задано), "
              f"RMS {db(float(np.sqrt((seg ** 2).mean()))):.1f} dB, "
              f"пик {db(float(np.abs(seg).max())):.1f} dBFS")
    elif peak > 0:
        gain = 10 ** (target_db / 20) / peak
        seg = seg * gain
        print(f"нормализация  : {db(gain):+.1f} dB, новый пик {db(float(np.abs(seg).max())):.1f} dBFS")

    sf.write(out, seg.astype(np.float32), rate, format="OGG", subtype="VORBIS")
    check, check_rate = sf.read(out, always_2d=True)
    print(f"записано      : {out}")
    print(f"проверка      : {check.shape[1]} канал(ов), {check_rate} Гц, "
          f"{len(check) / check_rate:.2f} с, пик {db(float(np.abs(check).max())):.1f} dBFS")


def cmd_selftest(path):
    """Проверяет, что обработка не искажает сигнал сама по себе.

    Круговорот stft→istft и шумодав с нулевым профилем шума обязаны быть
    тождественными преобразованиями. Если это не так — виноват код, а не запись.
    """
    mono, rate, _ = load_mono(path)
    seg = mono[int(7.95 * rate):int(9.95 * rate)]
    pad = FFT_SIZE

    padded = np.concatenate([np.zeros(pad), seg, np.zeros(pad)])
    rec = istft(stft(padded), len(padded))[pad:pad + len(seg)]
    err = float(np.abs(rec - seg).max())
    print(f"stft→istft, макс. ошибка : {err:.2e} = {db(err):.1f} dBFS")

    quiet = denoise(seg, np.zeros(FFT_SIZE * 4))
    err2 = float(np.abs(quiet - seg).max())
    print(f"шумодав с нулевым шумом  : {err2:.2e} = {db(err2):.1f} dBFS")

    ok = err < 1e-6 and err2 < 1e-6
    print("итог                     : " + ("в порядке" if ok else "ОШИБКА — обработка искажает сигнал"))
    return 0 if ok else 1


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "analyze" and len(argv) == 3:
        cmd_analyze(argv[2])
    elif cmd == "zoom" and len(argv) == 5:
        cmd_zoom(argv[2], float(argv[3]), float(argv[4]))
    elif cmd == "noise" and len(argv) == 5:
        cmd_noise(argv[2], float(argv[3]), float(argv[4]))
    elif cmd == "selftest" and len(argv) == 3:
        return cmd_selftest(argv[2])
    elif cmd == "cut" and len(argv) >= 6:
        rest = argv[6:]
        noise_range = None
        target_db, fade_ms, hp_hz = -1.0, 20.0, 0.0
        fixed_gain = None
        while rest:
            flag = rest.pop(0)
            if flag == "--denoise":
                noise_range = (float(rest.pop(0)), float(rest.pop(0)))
            elif flag == "--gain":
                target_db = float(rest.pop(0))
            elif flag == "--fade":
                fade_ms = float(rest.pop(0))
            elif flag == "--highpass":
                hp_hz = float(rest.pop(0))
            elif flag == "--fixed-gain":
                fixed_gain = float(rest.pop(0))
            else:
                raise SystemExit(f"неизвестный флаг {flag}")
        cmd_cut(argv[2], float(argv[3]), float(argv[4]), argv[5],
                noise_range, target_db, fade_ms, hp_hz, fixed_gain)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
