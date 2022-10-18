package midas.widgets

import chisel3._
import chisel3.util._
import freechips.rocketchip.config.Parameters
import midas.widgets._
import midas.targetutils._
import freechips.rocketchip.util.{DecoupledHelper}

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
  val out = Output(UInt((params.width).W))
}

class PlusargsBridgeHostIO(params: PlusargsBridgeParams)
                              (private val targetIO : PlusargsBridgeTargetIO = new PlusargsBridgeTargetIO(params)) 
                               extends Bundle with ChannelizedHostPortIO{
  def targetClockRef = targetIO.clock 
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
    val target = Module(new PlusargsBridge(params))
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

}

class PlusargsBridgeModule(params: PlusargsBridgeParams)(implicit p: Parameters) extends BridgeModule[PlusargsBridgeHostIO]()(p) {
  lazy val module = new BridgeModuleImp(this) {

    val io = IO(new WidgetIO())
    val hPort = IO(new PlusargsBridgeHostIO(params)())

    // bundle multiple genWOReg to support more width
    val plusargValue = genWOReg(Wire(UInt(32.W)), "out")  // fixme width as param
    val initDone = genWOReg(Wire(Bool()), "initDone")

    hPort.outChannel.valid := initDone
    hPort.outChannel.bits := plusargValue

    val plusargValueNext = RegNext(plusargValue)
    

    
    // only run if initDone is set
    assert(plusargValueNext === plusargValue)


    override def genHeader(base: BigInt, sb: StringBuilder) {
      import CppGenerationUtils._
      val headerWidgetName = getWName.toUpperCase
      super.genHeader(base, sb)
      sb.append(genConstStatic(s"${headerWidgetName}_message_count", UInt32((params.default))))
      sb.append(genConstStatic(s"${headerWidgetName}_foo", UInt32((42))))
    //   sb.append(genConstStatic(s"${headerWidgetName}_message_count", UInt32((params.conditionInfo).size)))
    //   sb.append(genArray(s"${headerWidgetName}_message_type", (params.conditionInfo).map(x => UInt32(if(x.isErr) 1 else 0))))
    //   sb.append(genArray(s"${headerWidgetName}_message", (params.conditionInfo).map(x => CStrLit(x.message))))
    }
    genCRFile()
  }
}
