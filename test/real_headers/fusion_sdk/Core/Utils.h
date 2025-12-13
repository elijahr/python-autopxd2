//////////////////////////////////////////////////////////////////////////////
//
// Copyright 2016 Autodesk, Inc. All rights reserved.
//
// Use of this software is subject to the terms of the Autodesk license
// agreement provided at the time of installation or download, or which
// otherwise accompanies this software.
//
//////////////////////////////////////////////////////////////////////////////

#pragma once

#include "OSMacros.h"

#ifdef XINTERFACE_EXPORTS
#ifdef __COMPILING_ADSK_UTILS_CPP__
#define ADSK_UTILS_API XI_EXPORT
#else
#define ADSK_UTILS_API
#endif
#else
#define ADSK_UTILS_API XI_IMPORT
#endif

namespace adsk
{
ADSK_UTILS_API bool terminate();

ADSK_UTILS_API bool autoTerminate();

ADSK_UTILS_API bool autoTerminate(bool value);

ADSK_UTILS_API bool doEvents();
} // namespace adsk
