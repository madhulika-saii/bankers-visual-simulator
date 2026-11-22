CC = gcc
CFLAGS = -Wall -Wextra -std=c11

all: bankers libbankers.so

# Compile the standalone C program
bankers: main.c bankers.c bankers.h
	$(CC) $(CFLAGS) main.c bankers.c -o bankers

# Build shared library for Python integration
libbankers.so: bankers.c bankers.h
	$(CC) $(CFLAGS) -fPIC -shared bankers.c -o libbankers.so

# Remove generated files
clean:
	rm -f bankers libbankers.so
