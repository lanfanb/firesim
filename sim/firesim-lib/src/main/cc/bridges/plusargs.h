
#ifndef __PLUSARGS_H
#define __PLUSARGS_H
//See LICENSE for license details.

#ifdef PLUSARGSBRIDGEMODULE_struct_guard

#include "bridges/bridge_driver.h"

class plusargs_t: public bridge_driver_t
{
  public:
    plusargs_t(simif_t* sim, 
    std::vector<std::string> &args,
    PLUSARGSBRIDGEMODULE_struct * mmio_addrs);
    ~plusargs_t();
    virtual void init();
    virtual void tick();
    virtual void finish() {};
    virtual bool terminate() { return test_done; };
    virtual int exit_code() { return fail; };
    const char* exit_message();

  private:
    PLUSARGSBRIDGEMODULE_struct * mmio_addrs;
    bool test_done = false;
    int fail = 0;
    int tick_rate = 10;
    int tick_counter = 0;
    int default_value = 0x40;
};
#endif // PLUSARGSBRIDGEMODULE_struct_guard
#endif //__PLUSARGS_H

