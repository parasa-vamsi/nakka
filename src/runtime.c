#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

extern int64_t _entry(void* heap); // asm("_entry");

int main(int argc, char** argv) {
  //printf("*********************************** \n");
  int64_t result = _entry((void*)malloc(4096));
  printf("%ld", result);
  //printf("*********************************** \n");
  return 0;
}