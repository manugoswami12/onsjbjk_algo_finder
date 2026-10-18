#include <string.h>
struct digit { const char *sym; int val; };
static const struct digit table[] = {{"M", 1000}, {"CM", 900}, {"D", 500}, {"C", 100}, {"X", 10}, {"V", 5}, {"I", 1}, {"", 0}};
void roman(int n, char *out) {
    const struct digit *d = table;
    out[0] = 0;
    while (d->val) {
        while (n >= d->val) {
            n -= d->val;
            strcat(out, d->sym);
        }
        d++;
    }
}
