"use client";

import { createTheme } from "@mantine/core";

export const theme = createTheme({
    primaryColor: 'blue',
    defaultRadius: 'md',
    fontFamily: '"Pretendard Variable", -apple-system, BlinkMacSystemFont, system-ui, Roboto, "Helvetica Neue", "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif',
    headings: {
        fontFamily: '"Pretendard Variable", sans-serif',
        fontWeight: "800", // Increased from 700
    },
    // Ensure default text is readable
    components: {
        Text: {
            defaultProps: {
                c: 'dark.9', // Default to near-black instead of grey
            }
        }
    },
    shadows: {
        md: '0 4px 20px rgba(0, 0, 0, 0.05)',
        xl: '0 8px 30px rgba(0, 0, 0, 0.12)',
    },
});
