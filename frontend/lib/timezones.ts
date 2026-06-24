// Common IANA timezones for campaign scheduling. The label shows a friendly name;
// the value is the IANA name passed to the backend (resolved with ZoneInfo).
export const TIMEZONES: { value: string; label: string }[] = [
  { value: "Asia/Kolkata", label: "IST — India (Asia/Kolkata)" },
  { value: "America/New_York", label: "ET — US Eastern (America/New_York)" },
  { value: "America/Chicago", label: "CT — US Central (America/Chicago)" },
  { value: "America/Denver", label: "MT — US Mountain (America/Denver)" },
  { value: "America/Los_Angeles", label: "PT — US Pacific (America/Los_Angeles)" },
  { value: "Europe/London", label: "UK — London (Europe/London)" },
  { value: "Europe/Berlin", label: "CET — Berlin (Europe/Berlin)" },
  { value: "Europe/Paris", label: "CET — Paris (Europe/Paris)" },
  { value: "Asia/Dubai", label: "GST — Dubai (Asia/Dubai)" },
  { value: "Asia/Singapore", label: "SGT — Singapore (Asia/Singapore)" },
  { value: "Australia/Sydney", label: "AEST — Sydney (Australia/Sydney)" },
  { value: "Pacific/Auckland", label: "NZST — New Zealand (Pacific/Auckland)" },
  { value: "UTC", label: "UTC" },
];

export const DEFAULT_TIMEZONE = "Asia/Kolkata";
