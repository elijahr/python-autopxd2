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
#ifdef __COMPILING_xIDEALLOCATOR_CPP__
#define xIDEALLOCATOR_API XI_EXPORT
#else
#define xIDEALLOCATOR_API
#endif
#else
#define xIDEALLOCATOR_API XI_IMPORT
#endif

#define DEALLOCATEARRAYINTERNAL(T)                                                                                     \
    namespace adsk                                                                                                     \
    {                                                                                                                  \
    namespace core                                                                                                     \
    {                                                                                                                  \
    xIDEALLOCATOR_API void DeallocateArrayInternal(T* p);                                                              \
    }                                                                                                                  \
    }

#define DEALLOCATEARRAYINTERNALCLASS(space, T)                                                                         \
    namespace adsk                                                                                                     \
    {                                                                                                                  \
    namespace space                                                                                                    \
    {                                                                                                                  \
    class T;                                                                                                           \
    }                                                                                                                  \
    }                                                                                                                  \
    DEALLOCATEARRAYINTERNAL(adsk::space::T*)

DEALLOCATEARRAYINTERNAL(char)
DEALLOCATEARRAYINTERNAL(char*)
DEALLOCATEARRAYINTERNAL(int)
DEALLOCATEARRAYINTERNAL(short)
DEALLOCATEARRAYINTERNAL(double)
DEALLOCATEARRAYINTERNAL(bool)
DEALLOCATEARRAYINTERNAL(float)
DEALLOCATEARRAYINTERNAL(size_t)
DEALLOCATEARRAYINTERNALCLASS(core, Base)

namespace adsk
{
namespace core
{
// Delete an allocated array returned from an interface.
template <class T> void DeallocateArray(T* p)
{
    DeallocateArrayInternal(p);
}
inline void DeallocateArray(char** p)
{
    DeallocateArrayInternal(p);
}

// Delete an allocated array of interfaces returned from an interface.
template <typename T> void DeallocateArray(T** p)
{
    DeallocateArrayInternal(reinterpret_cast<Base**>(p));
}

} // namespace core
} // namespace adsk

#undef xIDEALLOCATOR_API
