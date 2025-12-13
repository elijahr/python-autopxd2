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

#if defined(_WINDOWS) || defined(_WIN64)
#define XI_WIN
#elif defined(__APPLE__) && defined(__MACH__)
#define XI_OSX
#elif defined(__linux__)
#define XI_LINUX
#else
#error "Operating System Not Supported By Neutron.  Only Windows and Mac OS X Supported"
#endif

#if defined(XI_WIN)
#define XI_EXPORT __declspec(dllexport)
#define XI_IMPORT __declspec(dllimport)
#elif defined(XI_OSX) || defined(XI_LINUX)
#define XI_EXPORT __attribute__((visibility("default")))
#define XI_IMPORT __attribute__((visibility("default")))
#endif
