package com.beemer.math;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Number formatting copied from app/beemer.py (pct, num, inr, indian, crore, lakh). */
public final class IndianFormat {
    public static final String ENDASH = "–";
    public static final String MINUS = "−";

    private IndianFormat() {}

    public static String fixed(double x, int digits) {
        BigDecimal bd = new BigDecimal(Double.toString(x)).setScale(digits, RoundingMode.HALF_EVEN);
        return bd.toPlainString();
    }

    public static String pct(Double x, int d, boolean sign) {
        if (x == null || x.isNaN()) return ENDASH;
        String n = fixed(x * 100, d);
        if (sign && !n.startsWith("-")) n = "+" + n;
        return n + "%";
    }

    public static String pct(Double x) { return pct(x, 1, false); }

    public static String num(Double x, int d) {
        if (x == null || x.isNaN()) return ENDASH;
        return groupUs(fixed(x, d));
    }

    public static String num(Double x) { return num(x, 1); }

    public static String indian(double x, int d) {
        boolean neg = x < 0;
        String s = fixed(Math.abs(x), d);
        int dot = s.indexOf('.');
        String ip = dot < 0 ? s : s.substring(0, dot);
        String fp = dot < 0 ? "" : s.substring(dot + 1);
        if (ip.length() > 3) {
            String head = ip.substring(0, ip.length() - 3);
            String tail = ip.substring(ip.length() - 3);
            List<String> parts = new ArrayList<>();
            while (head.length() > 2) {
                parts.add(0, head.substring(head.length() - 2));
                head = head.substring(0, head.length() - 2);
            }
            if (!head.isEmpty()) parts.add(0, head);
            parts.add(tail);
            ip = String.join(",", parts);
        }
        return (neg ? "-" : "") + ip + (fp.isEmpty() ? "" : "." + fp);
    }

    public static String inr(Double x, int d) {
        if (x == null || x.isNaN()) return ENDASH;
        return "₹" + indian(x, d);
    }

    public static String inr(Double x) { return inr(x, 0); }

    public static String crore(Double x) {
        if (x == null || x.isNaN()) return ENDASH;
        String sign = x < 0 ? MINUS : "";
        double a = Math.abs(x);
        if (a >= 1e5) return sign + "₹" + groupUs(fixed(a / 1e5, 2)) + " lakh cr";
        return sign + "₹" + indian(a, 0) + " cr";
    }

    public static String lakh(double x) {
        if (x >= 1e7) return "₹" + groupUs(fixed(x / 1e7, 2)) + " crore";
        if (x >= 1e5) return "₹" + groupUs(fixed(x / 1e5, 2)) + " lakh";
        return inr(x, 0);
    }

    /** US thousands separators, matching Python's ``:,`` format. */
    public static String groupUs(String plain) {
        boolean neg = plain.startsWith("-");
        String body = neg ? plain.substring(1) : plain;
        int dot = body.indexOf('.');
        String ip = dot < 0 ? body : body.substring(0, dot);
        String fp = dot < 0 ? "" : body.substring(dot);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < ip.length(); i++) {
            if (i > 0 && (ip.length() - i) % 3 == 0) sb.append(',');
            sb.append(ip.charAt(i));
        }
        return (neg ? "-" : "") + sb + fp;
    }

    public static String signed(double x, int digits) {
        String n = fixed(x, digits);
        return n.startsWith("-") ? n : "+" + n;
    }

    public static String monthYear(java.time.LocalDate d) {
        return d.format(java.time.format.DateTimeFormatter.ofPattern("MMM yyyy", Locale.ENGLISH));
    }

    public static String dayMonthYear(java.time.LocalDate d) {
        return d.format(java.time.format.DateTimeFormatter.ofPattern("dd MMM yyyy", Locale.ENGLISH));
    }
}
