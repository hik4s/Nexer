const paths = {
  home: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  flows: "M5 4v6 M5 14v6 M19 4v6 M19 14v6 M8 7h8 M8 17h8 M12 7v10",
  play: "M8 4l12 8-12 8z",
  history: "M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l3 2",
  key: "M14 7a4 4 0 1 1 0 8 4 4 0 0 1 0-8z M10 12H3 M3 12v4 M6 12v3",
  studio: "M4 4h16v16H4z M4 9h16 M9 9v11 M13 13h3 M13 16h3",
  pulse: "M2 12h5l3-8 4 16 3-8h5",
  folder: "M3 6h7l2 3h9v11H3z",
  arrow: "M5 12h14 M13 6l6 6-6 6",
  search: "M10 3a7 7 0 1 1 0 14 7 7 0 0 1 0-14z M15 15l6 6",
  check: "M5 12l4 4L19 6",
};
export type IconName = keyof typeof paths;
export function Icon({name}: {name: IconName}) {
  return <svg className="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
