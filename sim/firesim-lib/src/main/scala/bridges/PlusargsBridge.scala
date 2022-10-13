
package midas.widgets

import chisel3._
import chisel3.util._
import freechips.rocketchip.config.Parameters
import midas.widgets._
import midas.targetutils._
import freechips.rocketchip.util.{DecoupledHelper}

/**
  * Defines a condition under which the simulator should halt. 
  * @param Message A string printed by the driver to indicate why the svimulator is terminating.
  * @param isError When true, instructs the driver to return a non-zero value when exiting under this condition.
**/
// case class TerminationCondition(isErr: Boolean, message : String)

// These are scala
// Signature copied from chipyard/generators/rocket-chip/src/main/scala/util/PlusArg.scala
case class PlusargsBridgeParams(
  name: String,
  default: BigInt = 0,
  docstring: String = "",
  width: Int = 32
)                

class PlusargsBridgeTargetIO(params: PlusargsBridgeParams) extends Bundle {
  val clock = Input(Clock())
//   val terminationCode = Input(UInt((log2Ceil((params.conditionInfo).size)).W))
// add an? output which is the plusargs value
  // val valid = Input(Bool()) 
  val out = Output(UInt((params.width).W))
  // val terminationCode = UInt((params.width).W)
}

class PlusargsBridgeHostIO(params: PlusargsBridgeParams)
                              (private val targetIO : PlusargsBridgeTargetIO = new PlusargsBridgeTargetIO(params)) 
                               extends Bundle with ChannelizedHostPortIO{
  def targetClockRef = targetIO.clock 
  //It is just inputs from the target to indicate test completion
  //The HostPort annotation would not work with aggregates so creating individual channels.
// //   val terminationCodeH = InputChannel(targetIO.terminationCode)
  // val validH = InputChannel(targetIO.valid)
  // val validH = true.B
  val outChannel = OutputChannel(targetIO.out)
}

class PlusargsBridge(params: PlusargsBridgeParams) extends BlackBox
    with Bridge[PlusargsBridgeHostIO, PlusargsBridgeModule] {
  val io = IO(new PlusargsBridgeTargetIO(params))
  val bridgeIO = new PlusargsBridgeHostIO(params)(io)

  val constructorArg = Some(params)

  generateAnnotations()
}

object PlusargsBridge {

  private def annotatePlusargsBridge(clock: Clock, reset: Reset, params: PlusargsBridgeParams): PlusargsBridge = {
    // val finish = true.B // conditionBools.reduce(_||_)
    // val errMessageID = PriorityEncoder(conditionBools)
    // require(params.conditionInfo.size==conditionBools.size)
    val target = Module(new PlusargsBridge(params))
    // target.io.terminationCode := errMessageID
    // target.io.valid := finish && !reset.asBool
    target.io.clock := clock
    target
  }

  // Signature copied from chipyard/generators/rocket-chip/src/main/scala/util/PlusArg.scala
  def apply(name: String, default: BigInt = 0, docstring: String = "", width: Int = 32): PlusargsBridge = {
    val params = PlusargsBridgeParams(name, default, docstring, width)
    annotatePlusargsBridge(Module.clock, Module.reset, params)

  }

  def apply(params: PlusargsBridgeParams): PlusargsBridge = {
    annotatePlusargsBridge(Module.clock, Module.reset, params)
  }

  def drive(params: PlusargsBridgeParams): UInt = {
    val target = annotatePlusargsBridge(Module.clock, Module.reset, params)
    target.io.out
  }


/** Instatiates the target side of the Bridge, selects one of 
 *  the available finish conditions and passes on the corresponding 
 *  error message.
 *  @param clock: Clock to the bridge which it must run on.
 *  @param reset: local reset for the bridge.
 *  @param conditionBools: Seq of finished conditions indicated by running programs
 *  @param params: Possible list of message info to be returned by simulator  
 */

  // def apply(clock: Clock, reset: Reset, conditionBools: Seq[Bool], params: PlusargsBridgeParams): PlusargsBridge = {
  //   annotatePlusargsBridge(clock, reset, conditionBools, params)
  // }

/** Simpler way to instantiate target side of the bridge by using implicit clock and reset
 */
  // def apply(conditionBools: Seq[Bool], params: PlusargsBridgeParams): PlusargsBridge = {
  //   annotatePlusargsBridge(Module.clock, Module.reset, conditionBools, params)
  // }

}

class PlusargsBridgeModule(params: PlusargsBridgeParams)(implicit p: Parameters) extends BridgeModule[PlusargsBridgeHostIO]()(p) {
  lazy val module = new BridgeModuleImp(this) {

    val io = IO(new WidgetIO())
    val hPort = IO(new PlusargsBridgeHostIO(params)())
    
    val statusDone = true.B
    // // val terminationCode = Queue(hPort.terminationCodeH)

    val cycleCountWidth = 64

    val tokenCounter = genWideRORegInit(0.U(cycleCountWidth.W), "out_counter") 

    // val noTermination = !statusDone.bits

    // val tFireHelper = DecoupledHelper(terminationCode.valid, statusDone.valid, noTermination)
    // val tFireHelper = true.B;

    // when(tFireHelper.fire) {
    //   tokenCounter := tokenCounter + 1.U
    // }

    // statusDone.ready := tFireHelper.fire(statusDone.valid)
    statusDone.ready := true.B
    // // terminationCode.ready := tFireHelper.fire(terminationCode.valid)

    //MMIO to indicate if the simulation has to be terminated
    genROReg(statusDone.bits && statusDone.valid, "out_status")
    //MMIO to indicate one of the target defined termination messages
    // // genROReg(terminationCode.bits, "out_terminationCode")

    override def genHeader(base: BigInt, sb: StringBuilder) {
      import CppGenerationUtils._
      val headerWidgetName = getWName.toUpperCase
      super.genHeader(base, sb)
      sb.append(genConstStatic(s"${headerWidgetName}_message_count", UInt32((params.default))))
    //   sb.append(genConstStatic(s"${headerWidgetName}_message_count", UInt32((params.conditionInfo).size)))
    //   sb.append(genArray(s"${headerWidgetName}_message_type", (params.conditionInfo).map(x => UInt32(if(x.isErr) 1 else 0))))
    //   sb.append(genArray(s"${headerWidgetName}_message", (params.conditionInfo).map(x => CStrLit(x.message))))
    }
    genCRFile()
  }
}
