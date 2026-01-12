/**
 * Global type declarations for browser globals
 * These are shared across all TypeScript files
 * 
 * ⚠️ IMPORTANT: This is a TypeScript declaration file.
 * - Edit this file: web_dashboard/src/js/globals.d.ts
 * - This file is automatically included by TypeScript
 * - DO NOT edit compiled .js files - they will be overwritten
 * 
 * NOTE: TypeScript compiles ALL files together, even though only one page
 * loads at runtime. This is why we centralize global declarations here.
 */

// Global browser APIs loaded from CDNs
declare global {
    interface Window {
        INITIAL_FUND?: string;
        marked?: {
            parse: (text: string) => string;
        };
        // agGrid is declared in files that use it (congress_trades.ts, etc.)
        // We don't declare it here to avoid conflicts with different type definitions
        agGrid?: any; // Use 'any' here as a fallback, specific files can override with proper types
    }
    
    // ApexCharts is loaded from CDN
    const ApexCharts: {
        new (element: HTMLElement, options: ApexChartsOptions): ApexChartsInstance;
    };
    
    interface ApexChartsOptions {
        series?: any[];
        chart?: {
            type?: string;
            height?: number;
            toolbar?: { show?: boolean };
            zoom?: { enabled?: boolean };
        };
        colors?: string[];
        stroke?: { curve?: string; width?: number };
        xaxis?: { type?: string };
        yaxis?: {
            labels?: {
                formatter?: (val: number) => string;
            };
        };
        tooltip?: {
            x?: { format?: string };
            y?: { formatter?: (val: number) => string };
        };
        labels?: string[];
    }
    
    interface ApexChartsInstance {
        render(): void;
        destroy(): void;
    }
}

// Export empty object to make this a module (required for declare global)
export {};
