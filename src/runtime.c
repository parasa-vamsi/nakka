#include <stdio.h>
#include <stdint.h>

extern int64_t _entry(); // asm("_entry");

int main(int argc, char** argv) {
  printf("*********************************** \n");
  int64_t result = _entry();
  printf("%ld\n", result);
  printf("*********************************** \n");
  return 0;
}