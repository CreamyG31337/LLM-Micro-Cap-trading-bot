/**
 * Shared TypeScript types for dashboard JavaScript
 */

export type Theme = 'system' | 'light' | 'dark' | 'midnight-tokyo' | 'abyss';
export type EffectiveTheme = Exclude<Theme, 'system'>;
export type ThemeChangeCallback = (theme: Theme) => void;
