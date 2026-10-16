/** Strict local wall-clock conversion. Never infer timezone or use Date.parse(). */
export type SiteDateFormat =
  'dd/MM/yyyy' | 'dd/MM/yyyy HH:mm' | 'dd/MM/yyyy HH:mm:ss' |
  'yyyy-MM-dd' | 'yyyy-MM-dd HH:mm:ss';

const supported = new Set<SiteDateFormat>([
  'dd/MM/yyyy','dd/MM/yyyy HH:mm','dd/MM/yyyy HH:mm:ss',
  'yyyy-MM-dd','yyyy-MM-dd HH:mm:ss'
]);

export function isSupportedSiteFormat(value: unknown): value is SiteDateFormat {
  return typeof value === 'string' && supported.has(value as SiteDateFormat);
}

function validDay(y: number, m: number, d: number, hh: number, mm: number, ss: number) {
  if (y < 1000 || y > 9999 || m < 1 || m > 12 || hh > 23 || mm > 59 || ss > 59) return false;
  return d >= 1 && d <= new Date(Date.UTC(y, m, 0)).getUTCDate();
}

function pieces(native: string): [string,string,string,string,string,string] | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(native);
  if (!match) return null;
  const [,y,m,d,hh='00',mm='00',ss='00'] = match;
  return validDay(+y,+m,+d,+hh,+mm,+ss) ? [y,m,d,hh,mm,ss] : null;
}

export function toNativeDateTime(raw: string, format: SiteDateFormat, hasTime: boolean): string | null {
  if (!raw) return '';
  if (!isSupportedSiteFormat(format)) return null;
  let native: string;
  if (format.startsWith('dd/MM/')) {
    const match = /^(\d{2})\/(\d{2})\/(\d{4})(?: (\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(raw);
    if (!match) return null;
    native = `${match[3]}-${match[2]}-${match[1]}` +
      (hasTime ? `T${match[4]??'00'}:${match[5]??'00'}:${match[6]??'00'}` : '');
  } else {
    native = hasTime ? raw.replace(' ', 'T') : raw;
  }
  const date = pieces(native);
  if (!date) return null;
  if (hasTime && !format.includes('HH:')) return null;
  if (!hasTime && format.includes('HH:')) return null;
  return hasTime ? `${date[0]}-${date[1]}-${date[2]}T${date[3]}:${date[4]}:${date[5]}` :
    `${date[0]}-${date[1]}-${date[2]}`;
}

export function toSiteDateTime(native: string, format: SiteDateFormat): string | null {
  if (!native) return '';
  if (!isSupportedSiteFormat(format)) return null;
  const date = pieces(native);
  if (!date) return null;
  const [y,m,d,hh,mm,ss] = date;
  const isTime = format.includes('HH:');
  if (isTime && !native.includes('T')) return null;
  const base = format.startsWith('dd/MM/') ? `${d}/${m}/${y}` : `${y}-${m}-${d}`;
  return !isTime ? base : base + ` ${hh}:${mm}` + (format.endsWith(':ss') ? `:${ss}` : '');
}
