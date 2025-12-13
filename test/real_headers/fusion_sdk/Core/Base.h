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

#include "Memory.h"

// THIS CLASS IS USED BY AN API CLIENT

#include "OSMacros.h"

#ifdef XINTERFACE_EXPORTS
#ifdef __COMPILING_xIBASE_CPP__
#define xIBASE_API XI_EXPORT
#else
#define xIBASE_API
#endif
#else
#define xIBASE_API XI_IMPORT
#endif

namespace Ns
{
class UniqueString;
}

namespace adsk
{
namespace core
{

// Base class for all xInterface classes. The functions in this
// class are visible to and callable by an API client.
// The class does RTTI via the pObject->query<T>() method.
class Base : public ReferenceCounted
{
  public:
    // All xInterface classes (except this one)
    // have to implement the following
    // and return a unique address that is based on the class name.
    // static const char* classType();
    // We will do this via code generation from NIDL.
    xIBASE_API static const char* classType();

    // Get the interfaceId of the most derived (most specific) type of this reference.
    virtual const char* objectType() const = 0;

    // Indicates if this object is still valid, i.e. hasn't been deleted
    // or some other action done to invalidate the reference.
    virtual bool isValid() const = 0;

    // This is used to do RTTI via a templatized pObject->query<T>() method.
    // It is used by API clients to do RTTI between xInterface classes.
    template <class T> Ptr<T> cast() const;

    // Debug aid to get the total live instance count
    xIBASE_API static size_t instances();

  protected:
    xIBASE_API Base(void);
    xIBASE_API virtual ~Base(void);

    // This is used to do RTTI via a templatized pObject->query_raw<T>() method.
    // It is used internally to do RTTI to implementation (e.g. xLayer) classes
    // (API clients will not have the implementation header files and can't do this).
    // Public for implementation convenience, but not intended for normal client use.
    // The result is equivalent to a cast and no reference count is added to the reference returned.
  public:
    template <class T> T* query() const
    {
        return static_cast<T*>(this->queryInterface(T::interfaceId())); //-V2571 //-V3546
    }

    // For internal use.  Just forwards to classType.
    static const char* interfaceId()
    {
        return classType();
    }

  protected:
    // This will be implemented in the xInterface classes via
    // code generation from NIDL.
    // The result is equivalent to a cast and no reference count is added to the reference returned.
    xIBASE_API virtual void* queryInterface(const char* interfaceId) const;
    virtual void* queryInterface(const Ns::UniqueString* id) const = 0;

  private:
    virtual void placeholderBase0()
    {
    }
    virtual void placeholderBase1()
    {
    }
    virtual void placeholderBase2()
    {
    }
    virtual void placeholderBase3()
    {
    }
    virtual void placeholderBase4()
    {
    }
    virtual void placeholderBase5()
    {
    }
    virtual void placeholderBase6()
    {
    }
    virtual void placeholderBase7()
    {
    }
    virtual void placeholderBase8()
    {
    }
    virtual void placeholderBase9()
    {
    }
    virtual void placeholderBase10()
    {
    }
    virtual void placeholderBase11()
    {
    }
    virtual void placeholderBase12()
    {
    }
    virtual void placeholderBase13()
    {
    }
    virtual void placeholderBase14()
    {
    }
    virtual void placeholderBase15()
    {
    }
};

template <class T> inline Ptr<T> Base::cast() const
{
    T* pT = query<T>();
    return Ptr<T>(pT, false);
}

} // namespace core
} // namespace adsk

#undef xIBASE_API
