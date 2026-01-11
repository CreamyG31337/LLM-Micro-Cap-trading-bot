/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getPlotlyLayout } from './chart_theme_utils';
import { Theme } from './types';

// Mock window.matchMedia since it's not implemented in jsdom by default
beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addListener: vi.fn(), // Deprecated
            removeListener: vi.fn(), // Deprecated
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });
});

describe('Chart Theme Utils', () => {
    describe('getPlotlyLayout', () => {
        it('returns light theme colors for light theme', () => {
            const layout = getPlotlyLayout('light');
            expect(layout.paper_bgcolor).toBe('white');
            expect(layout.plot_bgcolor).toBe('white');
            expect(layout.font.color).toBe('rgb(31, 41, 55)');
        });

        it('returns dark theme colors for dark theme', () => {
            const layout = getPlotlyLayout('dark');
            expect(layout.paper_bgcolor).toBe('rgb(31, 41, 55)');
            expect(layout.font.color).toBe('rgb(209, 213, 219)');
        });

        it('returns midnight-tokyo colors correctly', () => {
            const layout = getPlotlyLayout('midnight-tokyo');
            expect(layout.paper_bgcolor).toBe('#24283b');
            expect(layout.font.color).toBe('#c0caf5');
        });

        it('falls back to light theme if matchMedia is false for system', () => {
            // matchMedia mock set to false in beforeEach
            const layout = getPlotlyLayout('system');
            expect(layout.paper_bgcolor).toBe('white');
        });
    });
});
