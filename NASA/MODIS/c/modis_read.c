/**
 * @file modis_read.c
 * Read a MODIS HDF4 science product with the netCDF C library.
 *
 * netCDF-C built with --enable-hdf4 opens HDF4 files through nc_open().
 * Every HDF4 Scientific Data Set (SDS) appears as a netCDF variable.
 * This program prints the file format, lists the variables, then reads
 * one variable, applies the MODIS scale_factor / add_offset, masks
 * _FillValue and values outside valid_range, and prints a summary.
 *
 * Usage:
 *     modis_read FILE.hdf [VARIABLE]
 *
 * If VARIABLE is omitted, the first 2-D variable that is not Latitude
 * or Longitude is used.
 *
 * This is example code from the book "Earth Observation in Practice"
 * (https://tinyurl.com/43e26by6).
 *
 * Author: Edward Hartnett
 * Date: 2026-10-02
 */

#include <math.h>
#include <netcdf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ERR(e)                                                          \
    do {                                                                \
        fprintf(stderr, "Error: %s (line %d)\n", nc_strerror(e), __LINE__); \
        exit(2);                                                        \
    } while (0)

/** Return 1 if attribute NAME exists on VARID, 0 otherwise. */
static int
has_att(int ncid, int varid, const char *name)
{
    return nc_inq_attid(ncid, varid, name, NULL) == NC_NOERR;
}

/** Read a numeric attribute as double, or return DEFAULT_VALUE if absent. */
static double
att_double(int ncid, int varid, const char *name, double default_value)
{
    double value;

    if (nc_get_att_double(ncid, varid, name, &value))
        return default_value;
    return value;
}

/** Print a string attribute if it exists. */
static void
print_text_att(int ncid, int varid, const char *name)
{
    size_t len;
    char *text;

    if (nc_inq_attlen(ncid, varid, name, &len))
        return;
    if (!(text = calloc(len + 1, 1)))
        return;
    if (!nc_get_att_text(ncid, varid, name, text))
        printf("  %-14s %s\n", name, text);
    free(text);
}

/** Pick the first 2-D variable that is not a geolocation field. */
static int
default_varid(int ncid, int nvars)
{
    char name[NC_MAX_NAME + 1];
    int ndims;

    for (int v = 0; v < nvars; v++) {
        if (nc_inq_var(ncid, v, name, NULL, &ndims, NULL, NULL))
            continue;
        if (ndims == 2 && strcmp(name, "Latitude") && strcmp(name, "Longitude"))
            return v;
    }
    return -1;
}

int
main(int argc, char **argv)
{
    int ncid, varid, ndims, nvars, ngatts, format, mode, ret;
    int dimids[NC_MAX_VAR_DIMS];
    nc_type xtype;
    char name[NC_MAX_NAME + 1];
    size_t dimlen[NC_MAX_VAR_DIMS], n = 1, nvalid = 0;
    double *data, scale, offset, fill, vr[2] = {-INFINITY, INFINITY};
    double vmin = INFINITY, vmax = -INFINITY, sum = 0.0;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s FILE.hdf [VARIABLE]\n", argv[0]);
        return 1;
    }

    if ((ret = nc_open(argv[1], NC_NOWRITE, &ncid)))
        ERR(ret);

    /* An HDF4 file reports NC_FORMATX_NC_HDF4 as its extended format. */
    if ((ret = nc_inq_format_extended(ncid, &format, &mode)))
        ERR(ret);
    printf("%s\n  extended format: %s\n", argv[1],
           format == NC_FORMATX_NC_HDF4 ? "NC_FORMATX_NC_HDF4" : "not HDF4");

    if ((ret = nc_inq(ncid, NULL, &nvars, &ngatts, NULL)))
        ERR(ret);
    printf("  %d variables, %d global attributes\n\n", nvars, ngatts);

    /* List every SDS with its type and shape. */
    for (int v = 0; v < nvars; v++) {
        if ((ret = nc_inq_var(ncid, v, name, &xtype, &ndims, dimids, NULL)))
            ERR(ret);
        printf("  %-40s type %2d  (", name, xtype);
        for (int d = 0; d < ndims; d++) {
            size_t len;
            if ((ret = nc_inq_dimlen(ncid, dimids[d], &len)))
                ERR(ret);
            printf("%s%zu", d ? " x " : "", len);
        }
        printf(")\n");
    }

    if (argc > 2) {
        if ((ret = nc_inq_varid(ncid, argv[2], &varid)))
            ERR(ret);
    } else if ((varid = default_varid(ncid, nvars)) < 0) {
        fprintf(stderr, "No 2-D data variable found.\n");
        return 1;
    }

    if ((ret = nc_inq_var(ncid, varid, name, &xtype, &ndims, dimids, NULL)))
        ERR(ret);
    for (int d = 0; d < ndims; d++) {
        if ((ret = nc_inq_dimlen(ncid, dimids[d], &dimlen[d])))
            ERR(ret);
        n *= dimlen[d];
    }

    printf("\nVariable %s\n", name);
    print_text_att(ncid, varid, "long_name");
    print_text_att(ncid, varid, "units");

    /* Read the stored integers as double; scaling is applied below. */
    if (!(data = malloc(n * sizeof(double))))
        return 2;
    if ((ret = nc_get_var_double(ncid, varid, data)))
        ERR(ret);

    scale = att_double(ncid, varid, "scale_factor", 1.0);
    offset = att_double(ncid, varid, "add_offset", 0.0);
    fill = att_double(ncid, varid, "_FillValue", NAN);
    if (has_att(ncid, varid, "valid_range"))
        nc_get_att_double(ncid, varid, "valid_range", vr);
    printf("  scale_factor   %g\n  add_offset     %g\n", scale, offset);
    printf("  _FillValue     %g\n  valid_range    %g %g\n", fill, vr[0], vr[1]);

    /* MODIS follows the HDF4 convention: value = scale * (stored - offset). */
    for (size_t i = 0; i < n; i++) {
        double v;
        if (data[i] == fill || data[i] < vr[0] || data[i] > vr[1])
            continue;
        v = scale * (data[i] - offset);
        if (v < vmin)
            vmin = v;
        if (v > vmax)
            vmax = v;
        sum += v;
        nvalid++;
    }

    printf("  %zu of %zu values valid", nvalid, n);
    if (nvalid)
        printf("; min %.3f, max %.3f, mean %.3f", vmin, vmax, sum / nvalid);
    printf("\n");

    free(data);
    if ((ret = nc_close(ncid)))
        ERR(ret);
    return 0;
}
