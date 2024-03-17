/**
 *  testing java to Arduino via usb serial.
 *  !! if Arduino IDE is running port cannot be opened
 *  !! single instance only as well
 * 
 *  --  all processing, sequencing and timing to be done here,
 *      simply send the 5 card line of pinHex. 
 * 
 *  WORKS:
 *      ardy is receiving USB->Serial of ints to send as bytes to MCP23008
 *      load seqFile into textarea - is EDITABLE!
 *      read file to screen, send lines at timer to arduino
 *      rudimentary playhead line colour addition, tracks position
 * 
 *  TODO:
 *      lock the textarea when playing seq as can edit it otherwise
 *      unlock as well - edit mode?
 *      stop is a pause and then can resume, need a "back to start"
 *      filename visible in GUI, and line numbers to play
 *      get int from dropdown, send to card(s) selected
 * 
 *  FILE FORMAT:  
 *      4 card, |=separator, n=skip, 0.7=tempo, 2nd digits=not used
 *      19,0.7|10,0|19,0|n,0
 *      n,0|n,0|n,0|n,0
 *      14,0|n,0|31,0|n,0
 *      19,0|10,0|19,0|n,0
 * 
 *  
 */
package com.kaputnikgo.arduinotest;
import java.io.IOException;
import com.fazecast.jSerialComm.SerialPort;
import java.awt.Color;
import java.io.File;
import java.io.FileReader;
import java.util.Arrays;
import java.util.Timer;
import java.util.TimerTask;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.swing.text.BadLocationException;
import javax.swing.text.DefaultHighlighter;
import javax.swing.text.Highlighter;

/**
 *
 * @author kaputnikgo
 */

// Seq File filter set to .txt file only
class SeqTxtFilter extends javax.swing.filechooser.FileFilter {
    @Override
    public boolean accept(File file) {
        // Allow only directories, or files with ".txt" extension
        return file.isDirectory() || file.getAbsolutePath().endsWith(".txt");
    }
    @Override
    public String getDescription() {
        // This description will be displayed in the dialog,
        // hard-coded = ugly, should be done via I18N
        return "Text documents (*.txt)";
    }
}

public class TesterUI extends javax.swing.JFrame {

    SerialPort sp;
    final int SERIAL_ERROR = -1;
    final int STOP_BIT = 99;
    final int LINE_SIZE = 11;
    final int DEBUG_TIME = 1000;
    String[] seqLines;
    byte[] message;
    Timer timer;
    TimerTask timerTask;
    int seqLineCounter = 0;
    private Highlighter.HighlightPainter painter;
    private Object paintObject;
    
    // test vars below
    boolean bufferType = false;  // to flip between bufferA and bufferB
    byte[] bufferA = {1,7,2,8,3,9,4,10,5,11,STOP_BIT};
    byte[] bufferB = {1,12,2,13,3,14,4,115,5,16,STOP_BIT};
    
    /**
     * Creates new form TesterUI
     */
    public TesterUI() {
        initComponents();   
    }
 
/*
* 
*    Utility functions
*    
*/    
    private void outputStatus(String text) {
        text = "\n" + text;
        statusText.append(text);
        statusText.setCaretPosition(statusText.getDocument().getLength());
    }
    private void outputMulti(String text, int num) {
        text += num;
        outputStatus(text); 
    }  
    protected void scanPorts() {
        // not finding the USB serial... need hardcoded?
        outputStatus("Commence scan.");
        SerialPort[] serialPorts = SerialPort.getCommPorts();
        SerialPort liveSerialPort = null;
        for (SerialPort p: serialPorts) {
            p.openPort();
            if (p.isOpen()) {
                liveSerialPort = p;
                outputStatus("Found port:");
                outputStatus(liveSerialPort.getSystemPortName());
                System.out.println("HERE opened port = " + liveSerialPort.getSystemPortName());
                break;
            }
        }
        outputStatus("End scan.");
        toggleScan(false);
    }
    private void debugMessage() {
        // check what is in message[]
        System.out.println("message: " + Arrays.toString(message));
        /*
        for (byte element : message) {
           System.out.println("elements = " + element);
        }
        */
    }
/*
    testing seq send to arduino over usb serial
*/
    class SeqTestTimer extends TimerTask {
        SeqTestTimer() {
            //empty constructor
        }
        @Override
        public void run() {
            if (sp != null && sp.openPort()) {
                // has a USB serial connection and port is open 
            }
            int success = 0;
            bufferType = !bufferType;
            outputStatus("sendTestSeq bool: " + bufferType);
            if (bufferType) {
               success = sp.writeBytes​(bufferA, bufferA.length); 
            }
            else {
               success = sp.writeBytes​(bufferB, bufferB.length); 
            }
            
            if (success == SERIAL_ERROR) {
                outputMulti("send ERROR =  ", success); 
            }
        }
    } 
    private void sendTestSeq() {
        timer = new Timer();
        timer.schedule(new SeqTestTimer(), 0 , DEBUG_TIME);
    }
/*
* 
*    USB serial functions
*    
*/
    protected boolean openSerial() {
        // hard coded for spackbook air usb left port
        sp = SerialPort.getCommPort("/dev/cu.usbmodem14201");
        sp.setComPortParameters(9600, 8, 1, 0);
        sp.setComPortTimeouts(SerialPort.TIMEOUT_WRITE_BLOCKING, 0, 0);
        //sp.clearDTR(); // will stop the Ardy reset when loading, probs need it for dev
        if (sp.openPort()) {
            System.out.println("Port is open.");
            outputStatus("Port is open:");
            outputStatus(sp.getSystemPortName());
            return true;
        }
        else {
            System.out.println("Failed to open port.");
            outputStatus("Failed to open port.");
            return false;
        }
    }
    protected boolean closeSerial() {
        // check is open first
        if (sp.closePort()) {
            System.out.println("Port is closed.");
            outputStatus("Port is closed.");
            return true;
        }
        else {
            System.out.println("Failed to close port.");
            outputStatus("Failed to close port.");
            return false;
        }
    }

/*
* 
*    seq file functions
*    
*/  
    private void updatePlayhead() throws BadLocationException {
        // make a colour highlight at seqLineCounter as it plays
        // track its position
        // remove the previous lines colour addition
        if (paintObject != null) {
           seqTextOutput.getHighlighter().removeHighlight(paintObject);
        }        
        int startIndex = seqTextOutput.getLineStartOffset(seqLineCounter);
        int endIndex = seqTextOutput.getLineEndOffset(seqLineCounter);
        painter = new DefaultHighlighter.DefaultHighlightPainter(Color.RED);
        paintObject = seqTextOutput.getHighlighter().addHighlight(startIndex, endIndex, painter);
        seqTextOutput.setCaretPosition(startIndex);
    }
    protected void sendMessage() {
        //send it
        // called from a playSequence type function
        if (sp != null && sp.openPort()) {
            // has a USB serial connection and port is open 
            int success = 0;
            if (message.length > 0) {
                success = sp.writeBytes​(message, message.length);
            }
            if (success == SERIAL_ERROR) {
               outputMulti("send ERROR =  ", success); 
            }
            message = null;
        }
        else {
            // port not open fail here
        }
    }
    private void splitLine(String line) throws BadLocationException {
        // get into byte[] buffer, add STOP_BIT
        //outputStatus("splitLine: " + line);
        message = new byte[LINE_SIZE];
        // add card numbers
        int cardNum = 1;
        for (int i = 0; i < LINE_SIZE; ) {
            message[i] = (byte)cardNum;
            i+=2;
            cardNum++;
        }
        String[] cardVals = line.split("\\|");
        //only prints out values for number of cards in file
        System.out.println("cardVals[] = " + Arrays.toString(cardVals));
        String[] candy;
        int pinPos = 1; // message array position
        for (String cardVal : cardVals) {
            // this runs for all possible cards (x5)
            candy = cardVal.split(",");
            //account for the seq use of 'n'
            if ("n".equals(candy[0])) {
                message[pinPos] = 0;  
            }
            else {
                message[pinPos] = (byte)Integer.parseInt(candy[0]);
            }
            // advance to next card elements
            pinPos+=2;
        }

        message[10] = STOP_BIT;       
        // should have ie: [1,12,2,9,3,23,4,17,5,18,STOP_BIT]
        //debugMessage();
        sendMessage(); 
        updatePlayhead();
        seqLineCounter++;
    }
    
    class SeqTimer extends TimerTask {
        SeqTimer() {
            //empty constructor
        }
        @Override
        public void run() {
            try {
                //outputStatus("Line Count: " + seqLineCounter);
                splitLine(seqLines[seqLineCounter]);
            } 
            catch (BadLocationException ex) {
                Logger.getLogger(TesterUI.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
    }  
    private void readSeqText() {
        seqLines = seqTextOutput.getText().split("\\n");
        // iterate over the lines
        outputStatus("Line Count: " + seqLines.length);
        if (seqLines.length > 0) {
            timer = new Timer();
            // we have seqLines[]
            if (seqLineCounter <= seqLines.length) {
                timer.schedule(new SeqTimer(), 0 , DEBUG_TIME);
            }
            else {
                // reached end of array
                timer = null;
            }
        }
    }
    private void seqPlay() {
        // need checks here that file in textarea is good and locked etc
        seqTextOutput.setEditable(false);
        readSeqText();
        // below for testing basic seq sending
        //sendTestSeq();
    }
    private void loadSeqFile() {
        // load Seq .txt file from location to textarea
        int returnVal;
        returnVal = seqFileChooser.showOpenDialog(this);
        if (returnVal == seqFileChooser.APPROVE_OPTION) {
            File file = seqFileChooser.getSelectedFile();
            try {
                // display onscreen
                outputStatus("Loaded: " + file.getName());
                seqTextOutput.read( new FileReader( file.getAbsolutePath() ), null );
            } 
            catch (IOException ex) {
                System.out.println("ERROR - file access: " + file.getAbsolutePath());
            }
        } 
        else {
            System.out.println("File access cancelled");
        }
    }

/*
* 
*    GUI response functions
*    
*/  
    // need to now talk to Arduino code to do the talking to MCP23008 bits etc
    private void toggleConnectOn(boolean connection) {
        if (connection) {
            // is true for result of user connect
            connectButton.setBackground(Color.green);
            disconnectButton.setBackground(Color.gray);
            disconnectButton.setSelected(false);
        }
        else {
            // has error on connect
            connectButton.setBackground(Color.red);
            disconnectButton.setBackground(Color.gray);
        }
    }
    private void toggleConnectOff(boolean connection) {
        if (connection) {
            // is true for result of user disconnect
            disconnectButton.setBackground(Color.green);
            connectButton.setBackground(Color.gray);
            connectButton.setSelected(false);
        }
        else {
            disconnectButton.setBackground(Color.red);
            connectButton.setBackground(Color.gray);
        }
    }
    private void toggleScan(boolean scanit) {
        if (scanit) {
            scannerButton.setBackground(Color.green);
            scanPorts();
        }
        else {
           scannerButton.setBackground(Color.gray); 
        }
    }
    
/*
* 
*    TEST functions
*    
*/
    protected void testSerial(byte[] buffer, int size) {
        // sends an int to Arduino code that is waiting to read a byte
        //int writeBytes​(byte[] buffer, int bytesToWrite)      
        outputMulti("testSerial of size: ", size);
        int success = sp.writeBytes​(buffer, size);
        outputMulti("byte success =  ", success);
    }
    private void testSend() throws IOException, InterruptedException {
        // will send in multiples of 2 for valid pins with STOP_BIT added.
        // ardy does not include STOP_BIT in pin buffer
        byte[] buffer = {1,7,2,8,3,9,4,10,5,11,STOP_BIT};
        int success = sp.writeBytes​(buffer, buffer.length);
        if (success == SERIAL_ERROR) {
           outputMulti("send ERROR =  ", success); 
        }
        else {
            // has finished
            outputMulti("sendMessage length: ", buffer.length);
            outputMulti("send success =  ", success);
        }
        //testSerial(buffer, buffer.length);
    }
    // hopefully don't need this
    protected void readArdy() {
        // read something from ardy to ack seq buffer is ready?
        // repeat the ackByte value
        byte[] readBuf = {};
        int success = sp.readBytes(readBuf, 2);
        if (success == SERIAL_ERROR) {
           outputMulti("readArdy ERROR =  ", success);  
        }    
    }
    
    /**
     * This method is called from within the constructor to initialize the form.
     * WARNING: Do NOT modify this code. The content of this method is always
     * regenerated by the Form Editor.
     */
    @SuppressWarnings("unchecked")
    // <editor-fold defaultstate="collapsed" desc="Generated Code">//GEN-BEGIN:initComponents
    private void initComponents() {

        buttonGroup1 = new javax.swing.ButtonGroup();
        buttonGroup2 = new javax.swing.ButtonGroup();
        buttonGroup3 = new javax.swing.ButtonGroup();
        buttonGroup4 = new javax.swing.ButtonGroup();
        buttonGroup5 = new javax.swing.ButtonGroup();
        jScrollPane1 = new javax.swing.JScrollPane();
        jTextArea1 = new javax.swing.JTextArea();
        seqFileChooser = new javax.swing.JFileChooser();
        connectButton = new javax.swing.JToggleButton();
        disconnectButton = new javax.swing.JToggleButton();
        appTitle = new javax.swing.JLabel();
        card1radio = new javax.swing.JRadioButton();
        card2radio = new javax.swing.JRadioButton();
        card3radio = new javax.swing.JRadioButton();
        card4radio = new javax.swing.JRadioButton();
        card5radio = new javax.swing.JRadioButton();
        jComboBox1 = new javax.swing.JComboBox<>();
        jScrollPane2 = new javax.swing.JScrollPane();
        statusText = new javax.swing.JTextArea();
        scannerButton = new javax.swing.JToggleButton();
        sendButton = new javax.swing.JToggleButton();
        seqText = new javax.swing.JScrollPane();
        seqTextOutput = new javax.swing.JTextArea();
        seqPlay = new javax.swing.JToggleButton();
        stopButton = new javax.swing.JToggleButton();
        jMenuBar1 = new javax.swing.JMenuBar();
        jMenu1 = new javax.swing.JMenu();
        LoadSeq = new javax.swing.JMenuItem();
        Exit = new javax.swing.JMenuItem();
        jMenu2 = new javax.swing.JMenu();

        jTextArea1.setColumns(20);
        jTextArea1.setRows(5);
        jScrollPane1.setViewportView(jTextArea1);

        seqFileChooser.setDialogTitle("Select Seq File");
        seqFileChooser.setFileFilter(new SeqTxtFilter());

        setDefaultCloseOperation(javax.swing.WindowConstants.EXIT_ON_CLOSE);

        connectButton.setText("Connect");
        connectButton.setToolTipText("connect to USB serial");
        connectButton.setSize(new java.awt.Dimension(78, 23));
        connectButton.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                connectButtonActionPerformed(evt);
            }
        });

        disconnectButton.setText("Disconnect");
        disconnectButton.setToolTipText("disconnect USB serial");
        disconnectButton.setSize(new java.awt.Dimension(95, 23));
        disconnectButton.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                disconnectButtonActionPerformed(evt);
            }
        });

        appTitle.setText("WiLL-i-ROMS java GUI tester");
        appTitle.setHorizontalTextPosition(javax.swing.SwingConstants.CENTER);
        appTitle.setMixingCutoutShape(null);

        card1radio.setText("card1");
        card1radio.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                card1radioActionPerformed(evt);
            }
        });

        card2radio.setText("card2");
        card2radio.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                card2radioActionPerformed(evt);
            }
        });

        card3radio.setText("card3");
        card3radio.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                card3radioActionPerformed(evt);
            }
        });

        card4radio.setText("card4");
        card4radio.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                card4radioActionPerformed(evt);
            }
        });

        card5radio.setText("card5");
        card5radio.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                card5radioActionPerformed(evt);
            }
        });

        jComboBox1.setModel(new javax.swing.DefaultComboBoxModel<>(new String[] { "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31" }));

        statusText.setEditable(false);
        statusText.setColumns(20);
        statusText.setLineWrap(true);
        statusText.setRows(5);
        statusText.setText("Hello World!");
        statusText.setFocusable(false);
        jScrollPane2.setViewportView(statusText);

        scannerButton.setText("Scanner");
        scannerButton.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                scannerButtonActionPerformed(evt);
            }
        });

        sendButton.setText("Send");
        sendButton.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                sendButtonActionPerformed(evt);
            }
        });

        seqText.setName("seqText"); // NOI18N

        seqTextOutput.setColumns(20);
        seqTextOutput.setRows(5);
        seqText.setViewportView(seqTextOutput);

        seqPlay.setText("SEQ play");
        seqPlay.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                seqPlayActionPerformed(evt);
            }
        });

        stopButton.setLabel("STOP");
        stopButton.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                stopButtonActionPerformed(evt);
            }
        });

        jMenu1.setText("File");

        LoadSeq.setText("Load Seq");
        LoadSeq.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                LoadSeqActionPerformed(evt);
            }
        });
        jMenu1.add(LoadSeq);

        Exit.setLabel("Exit");
        Exit.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                ExitActionPerformed(evt);
            }
        });
        jMenu1.add(Exit);

        jMenuBar1.add(jMenu1);

        jMenu2.setText("Edit");
        jMenuBar1.add(jMenu2);

        setJMenuBar(jMenuBar1);

        javax.swing.GroupLayout layout = new javax.swing.GroupLayout(getContentPane());
        getContentPane().setLayout(layout);
        layout.setHorizontalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.TRAILING, false)
                    .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                        .addGroup(layout.createSequentialGroup()
                            .addGap(68, 68, 68)
                            .addComponent(appTitle))
                        .addGroup(layout.createSequentialGroup()
                            .addContainerGap()
                            .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                                .addGroup(layout.createSequentialGroup()
                                    .addComponent(card1radio)
                                    .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                    .addComponent(card2radio)
                                    .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                    .addComponent(card3radio)
                                    .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                    .addComponent(card4radio)
                                    .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                    .addComponent(card5radio))
                                .addGroup(layout.createSequentialGroup()
                                    .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.TRAILING)
                                        .addComponent(jComboBox1, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                                        .addComponent(connectButton))
                                    .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                                    .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                                        .addGroup(layout.createSequentialGroup()
                                            .addComponent(disconnectButton)
                                            .addGap(18, 18, 18)
                                            .addComponent(scannerButton))
                                        .addGroup(layout.createSequentialGroup()
                                            .addComponent(sendButton)
                                            .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                                            .addComponent(seqPlay)
                                            .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                            .addComponent(stopButton)))))))
                    .addGroup(layout.createSequentialGroup()
                        .addContainerGap()
                        .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.TRAILING)
                            .addComponent(jScrollPane2)
                            .addComponent(seqText, javax.swing.GroupLayout.Alignment.LEADING))))
                .addContainerGap(javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE))
        );
        layout.setVerticalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addContainerGap()
                .addComponent(appTitle)
                .addGap(18, 18, 18)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(connectButton)
                    .addComponent(disconnectButton)
                    .addComponent(scannerButton))
                .addGap(18, 18, 18)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(card1radio)
                    .addComponent(card2radio)
                    .addComponent(card3radio)
                    .addComponent(card4radio)
                    .addComponent(card5radio))
                .addGap(12, 12, 12)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(jComboBox1, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addComponent(sendButton)
                    .addComponent(seqPlay)
                    .addComponent(stopButton))
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                .addComponent(seqText, javax.swing.GroupLayout.DEFAULT_SIZE, 189, Short.MAX_VALUE)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                .addComponent(jScrollPane2, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE))
        );

        pack();
    }// </editor-fold>//GEN-END:initComponents
   
/*
*    
*       auto-gen functions from GUI
*
*/       
    private void connectButtonActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_connectButtonActionPerformed
        // toggle button for connect to USB serial
        // check for "checked" or on state first
        if (connectButton.isSelected()) {
            toggleConnectOn(openSerial());
        }
    }//GEN-LAST:event_connectButtonActionPerformed

    private void disconnectButtonActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_disconnectButtonActionPerformed
        // toggle button to disconnect from USB serial
        if (disconnectButton.isSelected()) {
            //
            toggleConnectOff(closeSerial());
        }
    }//GEN-LAST:event_disconnectButtonActionPerformed

    private void card1radioActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_card1radioActionPerformed
        // 
        if (card1radio.isSelected()) {
            // toggle CARD_1
            outputStatus("Card 1 selected.");
        }
        else {
            outputStatus("Card 1 deselected.");
        }
    }//GEN-LAST:event_card1radioActionPerformed

    private void card2radioActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_card2radioActionPerformed
        if (card2radio.isSelected()) {
            // toggle CARD_2
            outputStatus("Card 2 selected.");
        }
        else {
            outputStatus("Card 2 deselected.");
        }
    }//GEN-LAST:event_card2radioActionPerformed

    private void card3radioActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_card3radioActionPerformed
        if (card3radio.isSelected()) {
            // toggle CARD_3
            outputStatus("Card 3 selected.");
        }
        else {
            outputStatus("Card 3 deselected.");
        }
    }//GEN-LAST:event_card3radioActionPerformed

    private void card4radioActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_card4radioActionPerformed
        if (card4radio.isSelected()) {
            // toggle CARD_4
            outputStatus("Card 4 selected.");
        }
        else {
            outputStatus("Card 4 deselected.");
        }
    }//GEN-LAST:event_card4radioActionPerformed

    private void card5radioActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_card5radioActionPerformed
        if (card5radio.isSelected()) {
            // toggle CARD_5
            outputStatus("Card 5 selected.");
        }
        else {
            outputStatus("Card 5 deselected.");
        }
    }//GEN-LAST:event_card5radioActionPerformed

    private void scannerButtonActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_scannerButtonActionPerformed
        if (scannerButton.isSelected()) {
            toggleScan(true);
        }
        else {
            toggleScan(false);
        }
    }//GEN-LAST:event_scannerButtonActionPerformed

    private void sendButtonActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_sendButtonActionPerformed
        if (sendButton.isSelected()) {
            sendButton.setBackground(Color.green);
            try {
                testSend();
            }
            catch (Exception ex) {
                // all, caught above
            }
        } 
        else {
            sendButton.setBackground(Color.gray);
        }
    }//GEN-LAST:event_sendButtonActionPerformed

    private void LoadSeqActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_LoadSeqActionPerformed
        // load Seq .txt file from location
        loadSeqFile();
    }//GEN-LAST:event_LoadSeqActionPerformed

    private void ExitActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_ExitActionPerformed
        // close the whole application
        System.exit(0);
    }//GEN-LAST:event_ExitActionPerformed

    private void seqPlayActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_seqPlayActionPerformed
        // play the loaded seq from file
        if (seqPlay.isSelected()) {
            seqPlay.setBackground(Color.green);
            seqPlay();
        }
        else {
            seqPlay.setBackground(Color.gray);
        }
    }//GEN-LAST:event_seqPlayActionPerformed

    private void stopButtonActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_stopButtonActionPerformed
        // TODO add your handling code here:
        if (timer != null) {
            timer.cancel();
            seqPlay.setBackground(Color.red);
        }
    }//GEN-LAST:event_stopButtonActionPerformed

    /**
     * @param args the command line arguments
     */
    public static void main(String args[]) {
        /* Set the Nimbus look and feel */
        //<editor-fold defaultstate="collapsed" desc=" Look and feel setting code (optional) ">
        /* If Nimbus (introduced in Java SE 6) is not available, stay with the default look and feel.
         * For details see http://download.oracle.com/javase/tutorial/uiswing/lookandfeel/plaf.html 
         */
        try {
            for (javax.swing.UIManager.LookAndFeelInfo info : javax.swing.UIManager.getInstalledLookAndFeels()) {
                if ("Nimbus".equals(info.getName())) {
                    javax.swing.UIManager.setLookAndFeel(info.getClassName());
                    break;
                }
            }
        } catch (ClassNotFoundException ex) {
            java.util.logging.Logger.getLogger(TesterUI.class.getName()).log(java.util.logging.Level.SEVERE, null, ex);
        } catch (InstantiationException ex) {
            java.util.logging.Logger.getLogger(TesterUI.class.getName()).log(java.util.logging.Level.SEVERE, null, ex);
        } catch (IllegalAccessException ex) {
            java.util.logging.Logger.getLogger(TesterUI.class.getName()).log(java.util.logging.Level.SEVERE, null, ex);
        } catch (javax.swing.UnsupportedLookAndFeelException ex) {
            java.util.logging.Logger.getLogger(TesterUI.class.getName()).log(java.util.logging.Level.SEVERE, null, ex);
        }
        //</editor-fold>

        /* Create and display the form */
        java.awt.EventQueue.invokeLater(new Runnable() {
            public void run() {
                new TesterUI().setVisible(true);
            }
        });
    }

    protected javax.swing.JSpinner pinInt;
    // Variables declaration - do not modify//GEN-BEGIN:variables
    private javax.swing.JMenuItem Exit;
    private javax.swing.JMenuItem LoadSeq;
    private javax.swing.JLabel appTitle;
    private javax.swing.ButtonGroup buttonGroup1;
    private javax.swing.ButtonGroup buttonGroup2;
    private javax.swing.ButtonGroup buttonGroup3;
    private javax.swing.ButtonGroup buttonGroup4;
    private javax.swing.ButtonGroup buttonGroup5;
    private javax.swing.JRadioButton card1radio;
    private javax.swing.JRadioButton card2radio;
    private javax.swing.JRadioButton card3radio;
    private javax.swing.JRadioButton card4radio;
    private javax.swing.JRadioButton card5radio;
    private javax.swing.JToggleButton connectButton;
    private javax.swing.JToggleButton disconnectButton;
    private javax.swing.JComboBox<String> jComboBox1;
    private javax.swing.JMenu jMenu1;
    private javax.swing.JMenu jMenu2;
    private javax.swing.JMenuBar jMenuBar1;
    private javax.swing.JScrollPane jScrollPane1;
    private javax.swing.JScrollPane jScrollPane2;
    private javax.swing.JTextArea jTextArea1;
    private javax.swing.JToggleButton scannerButton;
    private javax.swing.JToggleButton sendButton;
    private javax.swing.JFileChooser seqFileChooser;
    private javax.swing.JToggleButton seqPlay;
    private javax.swing.JScrollPane seqText;
    private javax.swing.JTextArea seqTextOutput;
    private javax.swing.JTextArea statusText;
    private javax.swing.JToggleButton stopButton;
    // End of variables declaration//GEN-END:variables

}
