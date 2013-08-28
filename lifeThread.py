"""
==================================================================
                          Game of Life
==================================================================
(c) Christian J. Burnham, DT12127103, Dublin Institute of Technology, Jun 2013
------------------------------------------------------------------

This code implements the 'Game of Life' cellular automaton, using the rules 
invented by John Horton Conway.  

The code can also be used to perform searches for 'still lifes'.

Periodic (toroidal) boundary conditions are used for the 'simulation'.  

Still life searches are done within a 1-cell margin so that boundary conditions have no 
effect on the resulting patterns and each pattern 
remains a still-life when embedded in any larger board.
"""

from Tkinter import * 
from ttk import Scrollbar
from itertools import * 
import tkMessageBox,tkFileDialog
import os
import threading
import Queue,time

from random import randint

# Two global LIFO queues used to communicate between the GUI, which 
# runs on the main thread and the pattern producer which runs on another thread.

guiToPatternQueue = Queue.LifoQueue()
patternToGuiQueue = Queue.LifoQueue()


class Producer(threading.Thread):
    """
    The theaded producer class, which runs on a separate thread to the GUI.
    Its role is to produce Game of Life patterns which it puts on the patternToGuiQueue to 
    be read in by the consumer() method in the Controller class.
    """

    def __init__(self,stillSize,percentage,nrows,ncols,speedVar):
        threading.Thread.__init__(self)
        self.stillSize = stillSize
        self.nrows = nrows
        self.ncols = ncols
        self.percentage = percentage
        self.speedVar = speedVar

    def run(self):
        self.__stop = False
        self.pauseFlag = 1
        self.guiToPatternCounter = -1
        self.counter = 0
        self.enumerate = 0

        self.loop()

    def stop(self):
        self.__stop = True

    def loop(self):
        while True:
            self.checkInput()
            if self.pauseFlag == 0:
                self.pattern.update()
                self.putBoardOnQueue()
                ss = 0.0005* 1.5**(20.0 - self.speedVar)
                time.sleep(ss)
            else:
                time.sleep(0.05)
    

    def checkInput(self):
        """
        This method checks for commands coming from the GUI events, which have been placed on the 
        guiToPatternQueue
        """

        if self.__stop:
            raise _ThreadStop()
        try:
            command = guiToPatternQueue.get(block = False)
            guiToPatternCounter = command[1]
            if guiToPatternCounter > self.guiToPatternCounter:
                self.guiToPatternCounter = guiToPatternCounter
                if command[0] == "StartNewPattern":
                    self.startNewPattern()
                elif command[0] == "pause":
                    self.pauseFlag = 1
                elif command[0] == "play":
                    self.pauseFlag = 0
                elif command[0] =="clear":
                    self.clear()
                elif command[0] == "newRandomPattern":
                    self.percentage = command[2]
                    self.startNewPattern()
                    self.pauseFlag = 1
                elif command[0] == 'changeSpeedToNewValue':
                    self.speedVar = int(command[2])
                elif command[0] == 'setRowsAndCols':
                    nrows = command[2]
                    ncols = command[3]
                    self.makeNewRowsAndCols(nrows,ncols)
                elif command[0] == 'step':
                    self.step()
                elif command[0] == 'findStillLife':
                    self.enumerate = 1 - self.enumerate
                    if self.enumerate == 1: self.findStillLife()
                elif command[0] == 'setBoard':
                    board = command[2]
                    self.setBoard(board)
                elif command[0] == 'setStillSize':
                    n = command[2]
                    self.setStillSize(n)
                elif command[0] == 'saveFile':
                    file = command[2]
                    self.saveFile(file)
                elif command[0] == 'openFile':
                    file = command[2]
                    self.nrows = command[3]
                    self.ncols = command[4]
                    self.openFile(file)

        except Queue.Empty:
            pass


    def saveFile(self,file):
        print 'saving file'
        tuple = self.pattern.getTupleFromPattern()
            
        file.write("%s %s\n" %(self.nrows,self.ncols))
        gen = self.pattern.getGeneration()
        file.write("%s\n" %gen)
        file.write(str(tuple))

    def openFile(self,file):

        gen=int(file.readline())
        tuple = eval(file.read())
        self.pattern.setPatternFromTuple(tuple)
        self.pattern.setGeneration(gen)
        ncells = self.pattern.countNcells()
        self.putBoardOnQueue()

    def setBoard(self,board):
        self.pattern.setBoard(board)
        self.pattern.countNcells()
        self.putBoardOnQueue()

    def startNewPattern(self):
        self.pattern = Life(self.nrows,self.ncols,self.percentage)
        self.pattern.randomize(self.percentage)
        self.putBoardOnQueue()

    def playPauseGame(self):
        self.pauseFlag = 1 - self.pauseFlag

    def clear(self):
        try:
            self.pattern.makeBlankBoard()
            self.putBoardOnQueue()
        except:
            pass

    def makeNewRowsAndCols(self,nrows,ncols):
        self.nrows = nrows
        self.ncols = ncols
        self.startNewPattern()
        self.clear()

    def step(self):
        self.pattern.update()
        self.putBoardOnQueue()

    def setStillSize(self,n):
        self.stillSize = n

    def findStillLife(self):

        # Iterate over all patterns in a board of dimension (nrows-2)*(ncols-2), 
        # the size of the board within a 1 square safety margin around the perimeter.

        ncols_reduced = self.ncols - 2
        nrows_reduced = self.nrows - 2
        n = nrows_reduced*ncols_reduced

        for tuplej in combinations(xrange(n),self.stillSize):

            if self.enumerate == 0: break

            # reflected1, reflected2 and reflected3 hold representations of the pattern reflected horizontally, vertically and 
            # horizontally + vertically.
            # For square patterns, reflected4 swaps rows and columns, then reflected5, reflected6 and reflected7 are representations 
            # of reflected4 reflected horizontally, vertically and horizontally + vertically.

            reflected1=[]
            reflected2=[]
            reflected3=[]
            reflected4=[]
            reflected5=[]
            reflected6=[]
            reflected7=[]

            # iflag indicates whether the pattern has at least one live cell in the top-most row (within the margin)
            # jflag indicates whether the pattern has at least one live cell in the left-most column (within the margin)

            iflag = 0
            jflag = 0

            # Halt enumeration if the first live cell in the tuple is in a column more than half-way accross the width of the board.
            # All subsequent patterns are translations and rotations of patterns encountered so far.
            # Proof:  If the first cell is in row 0, then the reflection j -> ncols-1-j results in a pattern where j is 
            # less than half-way across the 
            # width of the board and so will already have been enumerated.  
            # If the first cell is not in row 0, then a translation can take the pattern to one which has its first cell in row 0.

            j0 = tuplej[0] % ncols_reduced
            if j0 > ncols_reduced - 1 - j0: break

            for m in tuplej:
                i = m / ncols_reduced
                j = m % ncols_reduced

                if i==0: iflag = 1
                if j==0: jflag = 1

                i2 = nrows_reduced - 1 - i
                j2 = j
                reflected1.append(i2*ncols_reduced + j2)

                i3 = i
                j3 = ncols_reduced - 1 - j
                reflected2.append(i3*ncols_reduced + j3)

                i4 = nrows_reduced-1-i
                j4 = ncols_reduced-1-j
                reflected3.append(i4*ncols_reduced + j4)

                # For square boards
                if self.nrows == self.ncols:
                    reflected4.append(j*ncols_reduced + i)
                    reflected5.append(j2*ncols_reduced + i2)
                    reflected6.append(j3*ncols_reduced + i3)
                    reflected7.append(j4*ncols_reduced + i4)


            # Check the pattern is not a tranlation.  Only count patterns which have a live cell in row 0 and a live cell in column 0.  
            # All other patterns may be considered translations.

            if iflag and jflag:

                # Only step pattern if it is not a reflection along either 4 of the symmetries of a rectangle or 8 symmetries of the square.

                if          tuplej <= tuple(sorted(reflected1)) and tuplej <= tuple(sorted(reflected2))\
                        and tuplej <= tuple(sorted(reflected3)):

                    # For square boards
                    if self.nrows != self.ncols or (tuplej <= tuple(sorted(reflected4))\
                        and tuplej <= tuple(sorted(reflected5)) and tuplej <= tuple(sorted(reflected6))\
                        and tuplej <= tuple(sorted(reflected7))):

                        # Convert pattern tuple to format for board of dimension nrows*ncols
                        list=[]
                        for val in tuplej:
                            i = 1 + val/ncols_reduced
                            j = 1 + val%ncols_reduced
                            list.append(i*self.ncols + j)

                        # Set the pattern from the tuple and plot it

                        tuplej2=tuple(list)
                        self.pattern.setPatternFromTuple(tuplej2)
                        ncells = int(self.stillSize)
                        self.pattern.setNcells(ncells)

                        self.checkInput()

                        self.putBoardOnQueue()
                        ss = 0.0005* 1.5**(20.0 - self.speedVar)
                        time.sleep(ss)



                        # Evolve the pattern for 1 generation
                        self.pattern.update()
                        tuplek = self.pattern.getTupleFromPattern()

                        # If it's a still life, the pattern before and after will be identical.  
                        # Print out the still lifes to the terminal.

                        if set(tuplej2) == set(tuplek): 
                            print('='*30)
                            print tuplej2
                            self.pattern.printBoard()

    def putBoardOnQueue(self):
        board = self.pattern.getBoard()
        ngen = self.pattern.getGeneration()
        ncells = self.pattern.getNcells()
        self.counter += 1

        # Safer to send a copy of the board on the queue.  

        board2=[[0 for j in xrange(self.ncols)] for i in xrange(self.nrows)]
        for i in range(self.nrows):
            for j in range(self.ncols):
                board2[i][j] = board[i][j]

        patternToGuiQueue.put([board2,self.counter,ngen,ncells,self.nrows,self.ncols])

class _ThreadStop(StopIteration): 
    """
    Dummy exception class
    """
    pass


class Life(object):
    """
    This object implements the game board and also holds the pattern.
    
    self.__nrows = number of rows
    self.__ncols = number of columns
    self.__board = 2D list (nrows x ncols) containing the pattern
    self.__neighbors = 2D List (nrows x ncols) containing the number of neighbors of each cell (in toroidal boundary conditions)
    self.__generation = the generation number of the pattern
    self.__ncells = the number of live cells currently in the pattern
    """
    def __init__(self,nrows,ncols,percentage):
        self.__nrows = nrows
        self.__ncols = ncols
        self.__board = []
        self.__neighbors = []
        self.__generation = 1
        self.__ncells = 0

        self.makeBlankBoard()

    def randomize(self,percentage):
        """
        Fill the board according to the percentage, where 0 < percentage < 100.
        """

        self.__board = []
        for i in xrange(self.__nrows):
            column=[]
            for j in xrange(self.__ncols):
                rint=0
                if randint(1,100) <= percentage:  
                    rint=1
                    self.__ncells += 1
                column.append(rint)
            self.__board.append(column)

    def setPatternFromTuple(self,tuple):
        """
        Creates a board pattern from a tuple, where the tuple encodes the 2D pattern as
        a list of 1D integers.
        """

        self.makeBlankBoard()
        # Use modular arithmetic to code 2D pattern as 1D values.
        for val in tuple:
            i = val/self.__ncols
            j = val%self.__ncols
            self.__board[i][j] = 1


    def getTupleFromPattern(self):
        """
        Use a list comprehension to generate a tuple from the pattern, where the tuple encodes the 2D pattern as
        a list of 1D integers.
        """
        patternList = [i*self.__ncols+j for i in xrange(self.__nrows) for j in xrange(self.__ncols) if self.__board[i][j]]
        return tuple(patternList)

    def __str__(self):
        """Print information about the board and pattern"""
        return "Game of Life board of %d rows and %d columns and having %d live cells." %(self.__nrows,self.__ncols,self.__ncells)
    

    def printBoardGraphics(self,canvas,cellWidth,drawMargin):
        """
        Displays a graphical representation of the board onto a tkinter canvas

        canvas = A tkinter canvas
        drawWidth = the size of the individual cells when plotted on the canvas.  (Width = Height)
        drawMargin = the width of the margin drawn around the board on the canvas
        """

        # First draw in grid
        for i in xrange(self.__ncols + 1):
            canvas.create_line(cellWidth*i + drawMargin,drawMargin,
                               cellWidth*i + drawMargin,cellWidth*(self.__nrows) + drawMargin)

        for j in xrange(self.__nrows + 1):
            canvas.create_line(drawMargin,cellWidth*j + drawMargin
                               ,cellWidth*(self.__ncols) + drawMargin,cellWidth*j + drawMargin)

        # Now draw in live cells
        for i in xrange(self.__ncols):
            for j in xrange(self.__nrows):
                if self.__board[j][i]:
                    canvas.create_rectangle(cellWidth*i + drawMargin,cellWidth*j + drawMargin,
                                            cellWidth*(i + 1) + drawMargin,cellWidth*(j+1) + drawMargin,fill='red')

    def printBoard(self):
        """
        Displays a textual representation of the board, output to the monitor window.
        """

        for i in xrange(self.__nrows):
            for j in xrange(self.__ncols):
                if self.__board[i][j]:
                    print("*"),
                else:
                    print("-"),
            print("")


    def makeBlankBoard(self):
        """
        Use a nested list comprehension to create self.__board as a blank 2D list of size nrows*ncols
        """
        self.__ncells = 0
        self.__board=[[0 for j in xrange(self.__ncols)] for i in xrange(self.__nrows)]

    def makeBlankNeighbors(self):
        """
        Use a nested list comprehension to create self.__neighbors as a blank 2D list of size nrows*ncols
        """
        self.__neighbors=[[0 for j in xrange(self.__ncols)] for i in xrange(self.__nrows)]

    def update(self):
        """
        Finds the pattern on the n+1 th step, from the pattern on the nth step 
        using Conway's rule-set.
        """

        # First build up 2D list of the number of neighbors around each cell
        self.__generation += 1
        self.makeBlankNeighbors()

        for i in xrange(self.__nrows):
            for j in xrange(self.__ncols):
                if self.__board[i][j]:
                    # Note use of periodic (toroidal) boundary conditions
                    iplus=(i + 1) % self.__nrows
                    iminus=(i - 1) % self.__nrows
                    jplus=(j + 1) % self.__ncols
                    jminus=(j - 1) % self.__ncols
                    self.__neighbors[iminus][jminus] += 1
                    self.__neighbors[iminus][j     ] += 1
                    self.__neighbors[iminus][jplus ] += 1
                    self.__neighbors[i     ][jminus] += 1
                    self.__neighbors[i     ][jplus ] += 1
                    self.__neighbors[iplus ][jminus] += 1
                    self.__neighbors[iplus ][j     ] += 1
                    self.__neighbors[iplus ][jplus ] += 1

        #Now apply Conway's rules

        for i in xrange(self.__nrows):
            for j in xrange(self.__ncols):
                if self.__board[i][j] == 0:
                    if self.__neighbors[i][j] == 3:
                        self.__board[i][j] = 1
                        self.__ncells += 1
                elif self.__neighbors[i][j] !=2 and self.__neighbors[i][j] !=3: 
                        self.__board[i][j] = 0
                        self.__ncells -= 1

    def countNcells(self):
        """
        sets self.__ncells to the number of live cells on the board
        """

        ncells=0
        for i in xrange(self.__nrows):
            for j in xrange(self.__ncols):
                if self.__board[i][j]: ncells += 1

        self.__ncells = ncells

    def getBoard(self):
        """
        getter for board.  Note, board is mutable, so changes to board outside of this class will also cause changes inside.
        """
        return self.__board

    def getGeneration(self):
        """
        getter for generation
        """
        return self.__generation

    def setGeneration(self,gen):
        """
        setter for generation
        """
        self.__generation = gen

    def getNcells(self):
        """
        getter for ncells
        """
        return self.__ncells

    def setNcells(self,nc):
        """
        setter for ncells
        """
        self.__ncells = nc
    
    def setBoard(self,board):
        """
        setter for board
        """
        self.__ncells = 0 
        for i in xrange(self.__nrows):
            for j in xrange(self.__ncols):
                self.__board[i][j] = board[i][j]
                if board[i][j]:
                    self.__ncells += 1


class Controller(object):
    """
    This object acts as the controller for the game and also 
    draws the interface using tkinter.

    self.__pause = A Boolean showing whether the game is playing/paused.
    self.__enumerate = A Boolean showing whether the game is searching for still-life patterns.
    self.__percentage = The fill density used to create a random pattern.
    self.__nrows = The initial number of rows.
    self.__ncols = The initial number of columns.
    self.__nevery = The graphical display is updated every nevery steps.
    self.__cellWidth = The size of the individual cells when plotted on the canvas.  (Width = Height)
    self.__drawMargin = the width of the margin drawn around the board on the canvas
    """

    def __init__(self):


        self.__pause=1
        self.__enumerate=0
        self.__percentage = 50
        self.__nrows = 50
        self.__ncols = 50
        self.__nevery = 1
        self.__drawMargin = 5

        self.__root = Tk()
        self.__root.title("Game of Life")
        self.__root.geometry("%dx%d" %(700,500))
        self.__root.minsize(256,440)

        self.__cellWidth = 8
        self.__stillSize = 8 
        self.__speedVar = 10

        self.lifeThread = Producer(self.__stillSize,self.__percentage,self.__nrows,self.__ncols,self.__speedVar)
        self.lifeThread.start()


        self.guiToPatternCounter = 0
        self.counter = 0 


        # Create main frames.  The left frame contains the controls and the right frame contains the canvas.

        self.__leftFrame = Frame(self.__root, background="white",
          borderwidth=5,  relief = RIDGE,
          width = 250,height = 2000 
          )
        self.__leftFrame.pack_propagate(0)
        self.__leftFrame.pack(side=LEFT)

        self.__rightFrame = Frame(self.__root, background="white",
          borderwidth=5,  relief = RIDGE,
          width = 2000,height = 2000
          )
        self.__rightFrame.pack(side=RIGHT) 
        self.__rightFrame.pack_propagate(0)

        labelfont = ('Ariel', 30, 'bold')
        self.__label = Label(self.__leftFrame,font=labelfont,text='Game of Life')
        self.__label.pack(pady=30)

        # Pack frames containing widgets.

        self.__toolFrame=ToolFrame(self.__leftFrame,self,pady=10)
        self.__toolFrame.pack(pady=10)
        
        self.__randomFrame=RandomFrame(self.__leftFrame,self,self.__percentage)
        self.__randomFrame.pack()

        self.__controlFrame = ControlFrame(self.__leftFrame,self)
        self.__controlFrame.pack()

        self.__sizeFrame = SizeFrame(self.__leftFrame,self,self.__nrows,self.__ncols)
        self.__sizeFrame.pack()

        self.__speedFrame = SpeedFrame(self.__leftFrame,self,self.__speedVar)
        self.__speedFrame.pack()

        self.__popFrame = PopFrame(self.__rightFrame,self)
        self.__popFrame.pack()

        self.__canvasFrame = CanvasFrame(self.__rightFrame,self)
        self.__canvasFrame.pack()

        self.__stillFrame= StillFrame(self.__leftFrame,self,pady = 50,stillSize = self.__stillSize)
        self.__stillFrame.pack()

        self.__percentage = int(self.__randomFrame.densityText.get())
        self.reshape()
        self.random()
        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["StartNewPattern",self.guiToPatternCounter])
        time.sleep(0.2)
        self.pauseButtonConfigure()
        self.consumer(self.__root)
        self.__root.mainloop()

    def consumer(self,root):
        try:
            st = 0 
            while True:
                boardData = patternToGuiQueue.get(block = False)
                counter = boardData[1]
                if counter > self.counter: 
                    break

            self.board = boardData[0]
            gen = boardData[2]
            ncells = boardData[3]
            self.counter = counter
            self.__popFrame.genLabel.config(text = str(gen))
            self.__popFrame.popLabel.config(text=str(ncells))

            if boardData[4] == self.__nrows and boardData[5] == self.__ncols:
                self.drawBoard(self.__canvasFrame.canvas,self.__cellWidth,self.__drawMargin)
        except Queue.Empty:
            pass

        self.__root.after(1,lambda:self.consumer(root))

    def drawBoard(self,canvas,cellWidth,drawMargin):
        """
        Displays a graphical representation of the board onto a tkinter canvas

        canvas = A tkinter canvas
        drawWidth = the size of the individual cells when plotted on the canvas.  (Width = Height)
        drawMargin = the width of the margin drawn around the board on the canvas
        """

        self.__canvasFrame.canvas.delete(ALL)
        # First draw in grid
        for i in xrange(self.__ncols + 1):
            canvas.create_line(cellWidth*i + drawMargin,drawMargin,
                               cellWidth*i + drawMargin,cellWidth*(self.__nrows) + drawMargin)

        for j in xrange(self.__nrows + 1):
            canvas.create_line(drawMargin,cellWidth*j + drawMargin
                               ,cellWidth*(self.__ncols) + drawMargin,cellWidth*j + drawMargin)

        # Now draw in live cells
        for i in xrange(self.__ncols):
            for j in xrange(self.__nrows):
                if self.board[j][i]:
                    canvas.create_rectangle(cellWidth*i + drawMargin,cellWidth*j + drawMargin,
                                            cellWidth*(i + 1) + drawMargin,cellWidth*(j+1) + drawMargin,fill='red')

        self.__canvasFrame.canvas.update()

    def quit(self):
        """
        Quits program
        """
        self.__pause = 1
        self.lifeThread.stop()
        self.__root.quit()

    def saveFile(self):
        """
        Saves the current pattern
        """

        file = tkFileDialog.asksaveasfile(mode='w',defaultextension = '.life')
        if file:
            self.guiToPatternCounter += 1
            guiToPatternQueue.put(['saveFile',self.guiToPatternCounter,file])

    def openFile(self):
        """
        Opens a pattern from a file
        """
        file = tkFileDialog.askopenfile(mode='r',defaultextension = '.life',filetypes=[('Life patterns','.life')])
        if file:

            rowsCols = file.readline().split(" ")
            self.__nrows = int(rowsCols[0])
            self.__ncols = int(rowsCols[1])

            self.__sizeFrame.rowsText.delete(0,"end")
            self.__sizeFrame.rowsText.insert(0,self.__nrows)

            self.__sizeFrame.colsText.delete(0,"end")
            self.__sizeFrame.colsText.insert(0,self.__ncols)
            self.reshape()

            self.guiToPatternCounter += 1
            guiToPatternQueue.put(['openFile',self.guiToPatternCounter,file,self.__nrows,self.__ncols])

    def reshape(self):
        """
        Used to reshape the canvas when either the number of rows or number of columns changes.
        """

        if not self.__sizeFrame.rowsText.get().isdigit():
            tkMessageBox.showinfo("Alert","Not an integer")
            return
        if not self.__sizeFrame.colsText.get().isdigit():
            tkMessageBox.showinfo("Alert","Not an integer")
            return

        self.__nrows = int(self.__sizeFrame.rowsText.get())
        self.__ncols = int(self.__sizeFrame.colsText.get())

        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["setRowsAndCols",self.guiToPatternCounter,self.__nrows,self.__ncols,])

        self.__canvasFrame.canvas.config(width=self.__cellWidth*self.__ncols + 2*self.__drawMargin,
                                      height = self.__cellWidth*self.__nrows + 2*self.__drawMargin)
        self.__canvasFrame.canvas.config(scrollregion=(0,0,self.__cellWidth*self.__ncols + 2*self.__drawMargin,
                                                           self.__cellWidth*self.__nrows + 2*self.__drawMargin))

    def clickCell(self,event,draw):
        """
        Called when the user clicks on the canvas, which makes the cell under the mouse go live.
        draw parameter:
        +1 draws a live cell on click
        -1 erases a live cell on click
        """

        i = int((self.__canvasFrame.canvas.canvasx(event.x - self.__drawMargin))/self.__cellWidth)
        j = int((self.__canvasFrame.canvas.canvasy(event.y - self.__drawMargin))/self.__cellWidth)

        if -1<i<self.__ncols  and -1<j<self.__nrows:

            redraw = 0
            if self.board[j][i] == 0 and draw == 1:
                self.board[j][i] = 1
                redraw = 1
            elif self.board[j][i] == 1 and draw == -1:
                self.board[j][i]=0
                redraw = 1

            if redraw:
                self.guiToPatternCounter += 1
                guiToPatternQueue.put(['setBoard',self.guiToPatternCounter,self.board])
                self.drawBoard(self.__canvasFrame.canvas,self.__cellWidth,self.__drawMargin)

    def pauseButtonConfigure(self):
        """
        Used to configure the pause button and to make sure its text reflects the value of 
        the Boolean self.__pause.
        """

        if self.__pause == 0:
            self.__controlFrame.pauseButton.config(text='pause')
            self.guiToPatternCounter += 1
            guiToPatternQueue.put(["play",self.guiToPatternCounter])
        else:
            self.__controlFrame.pauseButton.config(text='play')
            self.guiToPatternCounter += 1
            guiToPatternQueue.put(["pause",self.guiToPatternCounter])


    def clear(self):
        """
        Called when the 'clear' button is pressed.  
        """
        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["clear",self.guiToPatternCounter])
        # pauseButtonConfigure also puts a command on the queue.  Sleep of 0.2 s enables both commands to be read by pattern thread.
        time.sleep(0.2)
        self.__pause = 1
        self.pauseButtonConfigure()

    def random(self):
        """
        Called when the 'random' button is pressed.  Creates a new random pattern.
        """
        percentage = int(self.__randomFrame.densityText.get())

        self.__pause = 1
        self.pauseButtonConfigure()
        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["newRandomPattern",self.guiToPatternCounter,percentage])

    def findStillLife(self):
        """
        Called when the 'Find Still Lifes' button is pressed. 
        """
        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["findStillLife",self.guiToPatternCounter])
        self.__enumerate = 1 - self.__enumerate
        if self.__enumerate == 1:
            self.__stillFrame.enumerateButton.config(text='Abandon Search',command = self.findStillLife)
            # Disable all the buttons that shouldn't be clicked during the enumeration
            self.__controlFrame.pauseButton.config(state=DISABLED)
            self.__randomFrame.randomButton.config(state=DISABLED)
            self.__controlFrame.clearButton.config(state=DISABLED)
            self.__controlFrame.stepButton.config(state=DISABLED)
            self.__sizeFrame.rowsText.config(state=DISABLED)
            self.__sizeFrame.colsText.config(state=DISABLED)
            self.__randomFrame.densityText.config(state=DISABLED)
            self.__stillFrame.stillSizeText.config(state=DISABLED)
            self.__toolFrame.saveButton.config(state=DISABLED)
            self.__toolFrame.openButton.config(state=DISABLED)
            self.__toolFrame.quitButton.config(state=DISABLED)
        else:
            self.__stillFrame.enumerateButton.config(text='Find Still Lifes',command = self.findStillLife)
            #Enable all the buttons that were greyed out during the enumeration
            self.__controlFrame.pauseButton.config(state=NORMAL)
            self.__randomFrame.randomButton.config(state=NORMAL)
            self.__controlFrame.clearButton.config(state=NORMAL)
            self.__controlFrame.stepButton.config(state=NORMAL)
            self.__sizeFrame.rowsText.config(state=NORMAL)
            self.__sizeFrame.colsText.config(state=NORMAL)
            self.__randomFrame.densityText.config(state=NORMAL)
            self.__stillFrame.stillSizeText.config(state=NORMAL)
            self.__toolFrame.saveButton.config(state=NORMAL)
            self.__toolFrame.openButton.config(state=NORMAL)
            self.__toolFrame.quitButton.config(state=NORMAL)


    def playPauseGame(self):
        """
        Called when the pause or play button is pressed.
        The game loop is contained in the while-loop in this method.
        """
        self.__pause= 1 - self.__pause
        self.pauseButtonConfigure()
        
    def stepAndPlot(self):
        """
        Steps the game by one generation and plots the result.
        """
        self.guiToPatternCounter += 1
        guiToPatternQueue.put(["step",self.guiToPatternCounter])


class ControlFrame(Frame):
    """
    Frame containing clear button, pause button and step button.
    """
    def __init__(self,parent,caller,**args):
        Frame.__init__(self,parent,**args)
        self.pack()
        self.clearButton = Button(self,text='clear',command = caller.clear)
        self.clearButton.pack(side=LEFT)
        self.pauseButton = Button(self, text='pause',width=5, command = caller.playPauseGame)
        self.pauseButton.pack(side=LEFT)
        self.stepButton = Button(self, text='step',command = caller.stepAndPlot)
        self.stepButton.pack(side=LEFT)

class SizeFrame(Frame):
    """
    Frame containing rows and columns text entry
    """
    def __init__(self,parent,caller,nrows,ncols,**args):
        Frame.__init__(self,parent,**args)
        self.pack()

        self.rowLabel = Label(self,text="rows")
        self.rowLabel.pack(side=LEFT)
        self.rowsText = Spinbox(self,width=5,from_=1, to = 10000,command = caller.reshape)
        self.rowsText.pack(side=LEFT)
        self.rowsText.bind('<Return>',lambda event:caller.reshape())

        self.colLabel = Label(self,text="cols")
        self.colLabel.pack(side=LEFT)
        self.colsText = Spinbox(self,width=5,from_=1, to = 10000,command = caller.reshape)
        self.colsText.pack(side=LEFT)
        self.colsText.bind('<Return>',lambda event:caller.reshape())

        self.rowsText.delete(0,"end")
        self.rowsText.insert(0,nrows)

        self.colsText.delete(0,"end")
        self.colsText.insert(0,ncols)

class PopFrame(Frame):
    """
    Frame containing population and num. generations text.
    """
    def __init__(self,parent,caller,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.genTextLabel=Label(self,text="generation ")
        self.genLabel = Label(self,text="0")
        self.genTextLabel.pack(side=LEFT)
        self.genLabel.pack(side=LEFT)
        self.popTextLabel=Label(self,text='    population =')
        self.popLabel = Label(self,text="0")
        self.popTextLabel.pack(side=LEFT)
        self.popLabel.pack(side=LEFT)

class CanvasFrame(Frame):
    """
    Frame containing drawing canvas and scrollbars
    """
    def __init__(self,parent,caller,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.canvas = Canvas(self,scrollregion=(0,0,1000,1000)
                             ,background='white',cursor='pencil')
        self.canvas.bind("<Button-1>",lambda event:caller.clickCell(event,1))
        self.canvas.bind("<B1-Motion>",lambda event:caller.clickCell(event,1))
        self.canvas.bind("<Control-Button-1>",lambda event:caller.clickCell(event,-1))
        self.canvas.bind("<Control-B1-Motion>",lambda event:caller.clickCell(event,-1))
        vScroll = Scrollbar(self, orient = VERTICAL)
        vScroll.pack(side = RIGHT, fill=Y)
        vScroll.config(command = self.canvas.yview)
        hScroll = Scrollbar(self, orient = HORIZONTAL)
        hScroll.pack(side = BOTTOM, fill=X)
        hScroll.config(command = self.canvas.xview)
        self.canvas.config(xscrollcommand = hScroll.set, yscrollcommand = vScroll.set)
        self.canvas.pack(side=LEFT)

class StillFrame(Frame):
    """
    Frame containing Find Still Life button and still life size text entry.
    """
    def __init__(self,parent,caller,stillSize,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.enumerateButton = Button(self, text='Find Still Lifes',width = 13, command = caller.findStillLife)
        self.enumerateButton.pack(side=LEFT)

        self.sizeLabel=Label(self, text = '   n:')
        self.sizeLabel.pack(side=LEFT)

        self.stillSizeText = Spinbox(self,width=5,from_ = 1, to = 1000,command = self.stillVerify)
        self.stillSizeText.pack(side=LEFT)
        self.stillSizeText.delete(0,"end")
        self.stillSizeText.insert(0,stillSize)
        self.stillSizeText.bind('<Return>',lambda event:self.stillVerify())
        self.caller = caller

    def stillVerify(self):
        """
        Called to verify that text entry of the number of still lifes is integer
        """
        if not self.stillSizeText.get().isdigit():
            tkMessageBox.showinfo("Alert","Not an integer")
            return
        guiToPatternCounter = self.caller.guiToPatternCounter
        guiToPatternCounter += 1
        self.caller.guiToPatternCounter = guiToPatternCounter
        guiToPatternQueue.put(['setStillSize',guiToPatternCounter,int(self.stillSizeText.get())])


class RandomFrame(Frame):
    """
    Frame containing random button and random density text entry
    """
    def __init__(self,parent,caller,percentage,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.randomButton = Button(self,text='random',width=6,command = caller.random)
        self.randomButton.pack(side=LEFT)

        self.densLabel = Label(self,text = 'using %:')
        self.densLabel.pack(side = LEFT)

        self.densityText = Spinbox(self,width = 5, from_=0, to=100, command = caller.random)
        self.densityText.pack(side=LEFT)
        self.densityText.delete(0,"end")
        self.densityText.insert(0,percentage)
        self.densityText.bind('<Return>',lambda event:self.random())

class ToolFrame(Frame):
    """
    Frame containing save button, open button and quit button.
    """

    def __init__(self,parent,caller,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.saveButton = Button(self, text='Save',command = caller.saveFile)
        self.saveButton.pack(side=LEFT)
        self.openButton = Button(self, text='Open',command = caller.openFile)
        self.openButton.pack(side=LEFT)
        self.quitButton = Button(self, text = 'Quit',command = caller.quit)
        self.quitButton.pack(side=LEFT)

class SpeedFrame(Frame):
    """
    Frame containing speed slider and its label
    """

    def __init__(self,parent,caller,speedVar,**args):
        Frame.__init__(self,parent,**args)
        self.pack(side=TOP)

        self.speedVar = IntVar()
        self.speedLabel = Label(self,text = 'speed     ')
        self.speedLabel.pack(side=LEFT)
        self.speedSlider = Scale(self, from_=1, to = 20,orient = HORIZONTAL,variable = self.speedVar, command = self.test)
        self.speedSlider.set(speedVar)
        self.speedSlider.pack(side=LEFT)
        self.caller = caller

    def test(self,value):
        guiToPatternCounter = self.caller.guiToPatternCounter
        guiToPatternCounter += 1
        self.caller.guiToPatternCounter = guiToPatternCounter
        guiToPatternQueue.put(['changeSpeedToNewValue',guiToPatternCounter,value])

if __name__=="__main__": controller = Controller()
