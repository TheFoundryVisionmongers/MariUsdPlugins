#ifndef MARI_HOST_CONFIG_H
#define MARI_HOST_CONFIG_H

#if MARI_VERSION < 30
typedef MriGeoReaderHostV2 MriGeoReaderHost;
#else
typedef MriGeoReaderHostV4 MriGeoReaderHost;
#endif

#endif
