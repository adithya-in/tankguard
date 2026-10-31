import type { ChannelKey } from "../lib/types";

/* Authored 20×20 stroke icons for the five tank parameters. One stroke language —
   1.7px, round caps and joins, drawing style: measurement-instrument line art. */

interface IconProps {
  size?: number;
}

const base = {
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function TurbidityIcon({ size = 20 }: IconProps): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      {/* droplet with suspended particles — cloudiness in the water column */}
      <path {...base} d="M10 2.6c3 3.4 5.4 6.2 5.4 9a5.4 5.4 0 0 1-10.8 0c0-2.8 2.4-5.6 5.4-9Z" />
      <circle cx="8.1" cy="10.4" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="11.9" cy="12.6" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="10.2" cy="14.9" r="0.7" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TdsIcon({ size = 20 }: IconProps): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      {/* narrow beaker with settled solids — dissolved minerals made visible */}
      <path {...base} d="M6.6 3h6.8v8.4a3.4 3.7 0 0 1-6.8 0V3Z" />
      <path {...base} d="M5.4 3h9.2" />
      <circle cx="8.3" cy="13.2" r="0.85" fill="currentColor" stroke="none" />
      <circle cx="11.2" cy="14.6" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

function PhIcon({ size = 20 }: IconProps): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      {/* Erlenmeyer flask, clean and open — acidity measured */}
      <path {...base} d="M8.1 3v4.6l-3.9 7.2a2 2 0 0 0 1.8 2.9h8a2 2 0 0 0 1.8-2.9L12 7.6V3" />
      <path {...base} d="M6.9 3h6.2" />
      <path {...base} d="M5.9 12.2h8.2" />
    </svg>
  );
}

function TempIcon({ size = 20 }: IconProps): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      {/* thermometer: stem + bulb, mercury column */}
      <path {...base} d="M8.2 12.1V4.5a1.8 1.8 0 0 1 3.6 0v7.6a3.7 3.7 0 1 1-3.6 0Z" />
      <path {...base} d="M10 11.5V6.3" />
      <circle cx="10" cy="14.9" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

function LevelIcon({ size = 20 }: IconProps): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      {/* tank section with wavy waterline — how much water, not how deep */}
      <path {...base} d="M4.4 5h11.2v10.9a1.6 1.6 0 0 1-1.6 1.6H6a1.6 1.6 0 0 1-1.6-1.6V5Z" />
      <path {...base} d="M3 5h14" />
      <path {...base} d="M5.9 11.3c.9-1 1.8-1 2.7 0s1.8 1 2.7 0 1.8-1 2.7 0" />
      <path {...base} d="M6.4 14.6c.8-.9 1.6-.9 2.4 0s1.6.9 2.4 0 1.6-.9 2.4 0" />
    </svg>
  );
}

const ICONS: Record<ChannelKey, (p: IconProps) => React.JSX.Element> = {
  turb: TurbidityIcon,
  tds: TdsIcon,
  ph: PhIcon,
  temp: TempIcon,
  level: LevelIcon,
};

export function ParamIcon({ param, size }: { param: ChannelKey; size?: number }): React.JSX.Element {
  const Icon = ICONS[param];
  return <Icon size={size} />;
}
