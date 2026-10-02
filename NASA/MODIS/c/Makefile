# Build modis_read against a netCDF-C library that was built with HDF4.
# Override NC_CONFIG to point at a different installation.

NC_CONFIG ?= /usr/local/netcdf-c_hdf4/bin/nc-config
NC_PREFIX := $(shell $(NC_CONFIG) --prefix)

CFLAGS ?= -O2 -Wall -Wextra
CFLAGS += $(shell $(NC_CONFIG) --cflags)
LDLIBS += $(shell $(NC_CONFIG) --libs) -lm
LDFLAGS += -Wl,-rpath,$(NC_PREFIX)/lib

modis_read: modis_read.c

clean:
	rm -f modis_read

.PHONY: clean
