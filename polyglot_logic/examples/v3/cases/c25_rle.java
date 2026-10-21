import java.util.*;
class R {
    static List<String> encode(String s) {
        List<String> out = new ArrayList<>();
        int i = 0;
        while (i < s.length()) {
            int run = 1;
            while (i + run < s.length() && s.charAt(i + run) == s.charAt(i)) run++;
            out.add(run + "" + s.charAt(i));
            i += run;
        }
        return out;
    }
}
