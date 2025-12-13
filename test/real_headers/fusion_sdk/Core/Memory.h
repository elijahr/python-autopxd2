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

#include <cassert>
#include <exception>
#include <iterator>

// THESE TYPES ARE USED BY AN API CLIENT

#include "OSMacros.h"
#include "Deallocator.h"

#ifdef XINTERFACE_EXPORTS
#ifdef __COMPILING_xIMEMORY_CPP__
#define xIMEMORY_API XI_EXPORT
#else
#define xIMEMORY_API
#endif
#else
#define xIMEMORY_API XI_IMPORT
#endif

namespace adsk
{
namespace core
{

template <class Container, class PT> class Iterator;

class ReferenceCounted
{
  public:
    // Reference counting on the interface.  all interfaces returned from apis will have a reference count of
    // at least one, and the caller is responsible for calling release.  This reference counting should be hidden
    // from clients through smart pointer wrappers defined in the interface.
    virtual void addref() = 0;
    virtual void release() = 0;
    virtual int refcount() const = 0;
};

class IncompleteType
{
  public:
    template <typename T> static void addref(void* ptr)
    {
        reinterpret_cast<adsk::core::ReferenceCounted*>(ptr)->addref();
    }
    template <typename T> static void release(void* ptr)
    {
        reinterpret_cast<adsk::core::ReferenceCounted*>(ptr)->release();
    }
};

class CompleteType
{
  public:
    template <typename T> static void addref(T* ptr)
    {
        ptr->addref();
    }
    template <typename T> static void release(T* ptr)
    {
        ptr->release();
    }
};

template <class T, class PT = IncompleteType> class Ptr
{
  public:
    typedef T element_type;

    Ptr() : ptr_(nullptr)
    {
    }
    Ptr(const Ptr& rhs) : ptr_(nullptr)
    {
        reset(rhs.ptr_);
    }
    Ptr(const T* ptr, bool attach = true) : ptr_(nullptr)
    {
        reset(ptr, attach);
    }

    // casting constructor.  call operator bool to verify if cast was successful
    template <class V, class VPT> Ptr(const Ptr<V, VPT>& rhs) : ptr_(nullptr)
    {
        if (rhs)
        {
            reset(rhs->template query<T>(), false);
        }
    }

    ~Ptr()
    {
        reset(nullptr);
    }

    void operator=(const Ptr<T, PT>& rhs)
    {
        if (&rhs != this)
        {
            reset(rhs.ptr_);
        }
    }
    void operator=(const T* ptr)
    {
        reset(ptr, true);
    }

    // casting assignment operator.  call operator bool to verify if cast was successful
    template <class V, class VPT> void operator=(const Ptr<V, VPT>& rhs)
    {
        if (rhs)
        {
            reset(rhs->template query<T>(), false);
        }
        else
        {
            reset(nullptr);
        }
    }

    void reset(const T* ptr, bool attach = false)
    {
        if (ptr_ != ptr)
        {
            if (ptr_)
            {
                PT::template release<T>(ptr_);
            }
            ptr_ = const_cast<T*>(ptr);
            if (!attach && ptr_)
            {
                PT::template addref<T>(ptr_);
            }
        }
    }

    T* operator->() const
    {
        assert(ptr_ != nullptr);
        if (ptr_ == nullptr)
        {
            throw std::exception();
        }
        return ptr_;
    }

    // Test if this pointer is empty (if operator-> will throw)
    /*explicit*/ operator bool() const
    {
        return ptr_ != nullptr;
    }

    template <class V, class VPT> bool operator==(const Ptr<V, VPT>& rhs) const
    {
        return ptr_ == rhs.get();
    }

    template <class V, class VPT> bool operator!=(const Ptr<V, VPT>& rhs) const
    {
        return ptr_ != rhs.get();
    }

    template <class V, class VPT> bool operator<(const Ptr<V, VPT>& rhs) const
    {
        return ptr_ < rhs.get();
    }

    bool operator==(std::nullptr_t) const
    {
        return !ptr_;
    }
    bool operator!=(std::nullptr_t) const
    {
        return ptr_;
    }
    bool operator<(std::nullptr_t) const
    {
        return ptr_ < nullptr;
    }

    // Iteration support.  Only usable if T has count and item members and an iterable_type
    typedef Iterator<T, PT> iterator;
    iterator begin() const
    {
        return Iterator<T, PT>(*this);
    }
    iterator end() const
    {
        return Iterator<T, PT>(*this, true);
    }

    // Caution the following functions if used incorrectly can cause a reference count leak
    T* get() const
    {
        return ptr_;
    }
    T* getCopy() const
    {
        if (ptr_)
        {
            PT::template addref<T>(ptr_);
        }
        return ptr_;
    }
    T* detach()
    {
        T* t = ptr_;
        ptr_ = nullptr;
        return t;
    }

  private:
    T* ptr_;
};

template <class Container, class PT>
class Iterator : public std::iterator<std::input_iterator_tag, Ptr<typename Container::iterable_type, PT>>
{
  public:
    Iterator(const Ptr<Container, PT>& container, bool end = false) : container_(container), i_(0), end_(end)
    {
        if (!end && container_->count() == 0)
        {
            end_ = true;
        }
        assert(container_);
    }
    Iterator(const Iterator& rhs) : container_(rhs.container_), current_(rhs.current_), i_(rhs.i_), end_(rhs.end_)
    {
    }

    Iterator& operator++()
    {
        assert(!end_); // undefined to advance an iterator at end, but just noop
        if (!end_)
        {
            current_.reset(nullptr);
            assert(container_); // should never fire unless constructed improperly
            size_t count = container_->count();
            if (i_ < count)
            {
                ++i_;
            }
            if (i_ >= count)
            {
                end_ = true;
            }
        }
        return *this;
    }

    typename Iterator::value_type& operator*()
    {
        assert(!end_);
        assert(container_); // should never fire unless constructed improplerly
        if (!end_ && !current_ && container_)
        {
            current_ = container_->item(i_);
            assert(current_); // assume container is not poplulated with null values, so this should indicate a
                              // container error, check getLastError
        }
        return current_;
    }

    bool operator==(const Iterator& rhs) const
    {
        return container_ == rhs.container_ && end_ == rhs.end_ && (end_ || i_ == rhs.i_);
    }

    Iterator operator++(int)
    {
        Iterator tmp(*this);
        operator++();
        return tmp;
    }
    typename Iterator::value_type& operator->()
    {
        return operator*();
    }
    bool operator!=(const Iterator& rhs) const
    {
        return !operator==(rhs);
    }

  private:
    Ptr<Container, PT> container_;
    typename Iterator::value_type current_;
    size_t i_;
    bool end_;
};

} // namespace core
} // namespace adsk

#undef xIMEMORY_API
