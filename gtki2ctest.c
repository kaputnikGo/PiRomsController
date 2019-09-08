/* text the i2c library includes and polling */
/* gtki2ctest.c */
/* build with: gcc -Wall -g gtki2ctest.c -o gtki2ctest -lwiringPi `pkg-config --cflags --libs gtk+-2.0` */
/* bugs check:  sudo i2cdetect -y 1 */

#include <gtk/gtk.h>
#include <wiringPi.h>
#include <wiringPiI2C.h>
#include <string.h>

#define IODIR_REG 0x00
#define GPIO_REG 0x09

#define CARDSNUM 5
#define PINSNUM 32

/*
 * 	TODO
 *  - couple of lines of console display below buttons
 * 		- as a gtk_scrolled_window
 * 	- tracker window, also as a gtk_scrolled_window
 *  - menu bar
 *  - 2 views : compose and perform
 * 	- proper the name and file(s)
 * 
 */

struct Card {
	char *name; /* card1 etc */
	int address; /* i2c addr: 0x20 etc */
	int fd; /* file descr of card */
	struct Card *next; /* if ever linked */
};

/* struct Card card1, card2, card3, card4, card5; */
struct Card Cards[CARDSNUM];
int user_card_num;

/* function declarations */
gboolean init_cards();
void print_card(int candidate);
void card_select(GtkWidget *widget, gpointer data);
gboolean card_ready(int candidate);
int get_card_num_by_name(char *seek);

void card_presence(GtkWidget *widget, gpointer data);
void card_polling(GtkWidget *widget, gpointer data);
void play_all_test(GtkWidget *widget, gpointer data);
void console_print(char *message);


char *cardNames[CARDSNUM] = {
	"card1", "card2", "card3", "card4", "card5"
	};
	
int cardAddrs[CARDSNUM] = {
	0x20, 0x21, 0x22, 0x23, 0x24
	};
	
int pinsArray[PINSNUM] = {
	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 
	0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
	0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 
	0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F
	};

GtkTextBuffer *console_buffer;

static gboolean delete_event(GtkWidget *widget, GdkEvent *event, gpointer data) {
	/* return false here will destroy window
	* return true means don't destroy, ie can pop dialog */
	gtk_main_quit();
	return FALSE;
}
 
int main(int argc, char *argv[]) {
	GtkWidget *window;
	GtkWidget *fixed;
	GtkWidget *radio_box;
	GtkWidget *radio_card1, *radio_card2, *radio_card3, *radio_card4, *radio_card5;
	GtkWidget *separator;
	GtkWidget *button_presence, *button_polling, *button_test;
	GtkWidget *console_window, *console_view;
	GdkColor console_text_color, console_back_color;
	 

	gtk_init(&argc, &argv);
	 
/* wiringPi stuff */
	wiringPiSetup();
	
/* enum the controller cards */	
	if (init_cards()) {
		/* all cards populated */
		user_card_num = 0;
	} 	 
	 
/* GTK UI */
	window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
	gtk_window_set_default_size(GTK_WINDOW(window), 800, 600);
	gtk_window_set_resizable(GTK_WINDOW(window), FALSE);
	gtk_window_set_title(GTK_WINDOW(window), "WiLL-i-ROMS prototype");
	 
	/* add a fixed layout container */
	fixed = gtk_fixed_new();
	gtk_container_add(GTK_CONTAINER(window), fixed);

	g_signal_connect(window, "delete_event", G_CALLBACK(delete_event), NULL);
	gtk_container_set_border_width(GTK_CONTAINER(window), 10);
	
/* card selector radio buttons group */
	radio_box = gtk_hbox_new(FALSE, 5);
	gtk_fixed_put(GTK_FIXED(fixed), radio_box, 5, 5);
	gtk_widget_set_size_request(radio_box, 480, 40);
	
	/* null group, add other radios with prev card widget */
	radio_card1 = gtk_radio_button_new_with_label(NULL, Cards[0].name);
	gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(radio_card1), TRUE);
	g_signal_connect(radio_card1, "toggled", G_CALLBACK(card_select), (gpointer)0);
	gtk_box_pack_start(GTK_BOX(radio_box), radio_card1, TRUE, TRUE, 0);
	
	radio_card2 = gtk_radio_button_new_with_label_from_widget(GTK_RADIO_BUTTON(radio_card1), Cards[1].name);
	g_signal_connect(radio_card2, "toggled", G_CALLBACK(card_select), (gpointer)1);
	gtk_box_pack_start(GTK_BOX(radio_box), radio_card2, TRUE, TRUE, 0);
	
	radio_card3 = gtk_radio_button_new_with_label_from_widget(GTK_RADIO_BUTTON(radio_card2), Cards[2].name);
	g_signal_connect(radio_card3, "toggled", G_CALLBACK(card_select), (gpointer)2);
	gtk_box_pack_start(GTK_BOX(radio_box), radio_card3, TRUE, TRUE, 0);
	
	radio_card4 = gtk_radio_button_new_with_label_from_widget(GTK_RADIO_BUTTON(radio_card3), Cards[3].name);
	g_signal_connect(radio_card4, "toggled", G_CALLBACK(card_select), (gpointer)3);
	gtk_box_pack_start(GTK_BOX(radio_box), radio_card4, TRUE, TRUE, 0);
	
	radio_card5 = gtk_radio_button_new_with_label_from_widget(GTK_RADIO_BUTTON(radio_card4), Cards[4].name);
	g_signal_connect(radio_card5, "toggled", G_CALLBACK(card_select), (gpointer)4);
	gtk_box_pack_start(GTK_BOX(radio_box), radio_card5, TRUE, TRUE, 0);

/* separator above buttons */
	separator = gtk_hseparator_new();
	gtk_fixed_put(GTK_FIXED(fixed), separator, 5, 45);
	gtk_widget_set_size_request(separator, 480, 2);
	 
/* card presence button */
	button_presence = gtk_button_new_with_label("Check card");
	gtk_fixed_put(GTK_FIXED(fixed), button_presence, 20, 50);
	gtk_widget_set_size_request(button_presence, 100, 30);
	g_signal_connect(button_presence, "clicked", G_CALLBACK(card_presence), (gpointer)"button_presence");
	 
/* card polling button */
	button_polling = gtk_button_new_with_label("Poll card");
	gtk_fixed_put(GTK_FIXED(fixed), button_polling, 180, 50);
	gtk_widget_set_size_request(button_polling, 100, 30);
	g_signal_connect(button_polling, "clicked", G_CALLBACK(card_polling), (gpointer)"button_polling");

/* play_all_test button */
	button_test = gtk_button_new_with_label("Test all pins");
	gtk_fixed_put(GTK_FIXED(fixed), button_test, 340, 50);
	gtk_widget_set_size_request(button_test, 100, 30);
	g_signal_connect(button_test, "clicked", G_CALLBACK(play_all_test), (gpointer)"button_test");

/* console window */
	console_window = gtk_scrolled_window_new(NULL, NULL);
	gtk_container_set_border_width(GTK_CONTAINER(console_window), 5);
	gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(console_window),
		GTK_POLICY_AUTOMATIC, GTK_POLICY_ALWAYS);
	gtk_fixed_put(GTK_FIXED(fixed), console_window, 5, 85);
	gtk_widget_set_size_request(console_window, 480, 100);
	/* console text view */
	console_view = gtk_text_view_new();
	gtk_text_view_set_editable(GTK_TEXT_VIEW(console_view), FALSE);
	gtk_text_view_set_left_margin(GTK_TEXT_VIEW(console_view), 5);
	gdk_color_parse("green", &console_text_color);
	gdk_color_parse("black", &console_back_color);
	gtk_widget_modify_text(console_view, GTK_STATE_NORMAL, &console_text_color);
	gtk_widget_modify_base(console_view, GTK_STATE_NORMAL, &console_back_color);
	console_buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(console_view));
	console_print("WiLL-i-ROMS\nPrototype sequencer.\nConsole window for message printouts.");
	gtk_scrolled_window_add_with_viewport(GTK_SCROLLED_WINDOW(console_window), console_view);
	
	
/* main gtk run */
	gtk_widget_show_all(window);
	gtk_main();
	return 0;
}

/* 
 * 
 * 
 * controller card functions 
 * 
 * 
 * */
gboolean init_cards() {
	/* go through the structs and populate */
	int i;
	for (i = 0; i < CARDSNUM; ++i) {
		Cards[i].name = cardNames[i];
		Cards[i].address = cardAddrs[i];
		Cards[i].fd = wiringPiI2CSetup(Cards[i].address);

		if (card_ready(i)) {
			g_print("%s ready...\n", Cards[i].name);
		
			int writeReg = wiringPiI2CWriteReg8(Cards[i].fd, IODIR_REG, 0x00);
			if (writeReg == -1) {
				g_print("\nError writing to IODIR register for %s.\n", Cards[i].name);
			}
			else {				
				int readReg = wiringPiI2CReadReg8(Cards[i].fd, IODIR_REG);		
				g_print("%s IODIR: 0x%02X \n", Cards[i].name, readReg);
			}
		}
		else {
			return FALSE;
		}
	}
	return TRUE;
}
 
void print_card(int candidate) {
	g_print("Card name: %s\n", Cards[candidate].name);
	g_print("Card address: 0x%02X\n", Cards[candidate].address);
	g_print("Card fd: %d\n", Cards[candidate].fd);
	/* need a function to concatenate chars and return them */
	console_print(Cards[candidate].name);
}

void card_select(GtkWidget *widget, gpointer data) {
	/* radio button select card to enum and test */
	if (gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget))) {
		user_card_num = (gint)data;
		g_print("card_select for %s.\n", Cards[user_card_num].name);
	}
}

gboolean card_ready(int candidate) {
	/* Cards[x].fd is a linux file descriptor for the card address */
	if (Cards[candidate].fd == -1) {
		/* card 1 device failed to init */
		g_print("%s not ready error.\n", Cards[candidate].name);
		return FALSE;
	}		
	return TRUE;
}

int get_card_num_by_name(char *seek) {
	/* return a card from name search, not like this */
	int i;
	for (i = 0; i < CARDSNUM; ++i) {
		if (strcmp(Cards[i].name, seek)) return i;
	}
	/* catch */
	return 0;
}

/* 
 * 
 * 
 * button functions 
 * 
 * 
 * */
void card_presence(GtkWidget *widget, gpointer data) {
	/* check the presence of i2c bus cards here */
	if (card_ready(user_card_num)) {
		print_card(user_card_num);
	}
	g_print("Card presence check end - %s was pressed.\n", (gchar *)data);
}

void card_polling(GtkWidget *widget, gpointer data) {
	/* check the ouptput send of attached devices on i2c bus here */
    /* (0x00) reset first, then (0x01) card1: blaster sound */
	int writeReg = wiringPiI2CWriteReg8(Cards[user_card_num].fd, GPIO_REG, 0x00);
	if (writeReg == -1) {
		g_print("\nError writing to GPIO register for %s.\n", Cards[user_card_num].name);
	}
	else {
		wiringPiI2CWriteReg8(Cards[user_card_num].fd, GPIO_REG, 0x01);
	}
		
	g_print("Card polling check end - %s was pressed\n", (gchar *)data);
}

void play_all_test(GtkWidget *widget, gpointer data) {
	/* test trigger all the pins for a given device */
	/* need to trigger 0x00 before each sound */
	/* check writeReg first for any errors */
	int i;
	int writeReg = wiringPiI2CWriteReg8(Cards[user_card_num].fd, GPIO_REG, 0x00);
	if (writeReg == -1) {
		g_print("\nError writing to GPIO register for %s.\n", Cards[user_card_num].name);
	}
	else {
		// loop to play all pins
		g_print("\nTest all sounds for %s\n", Cards[user_card_num].name);
		for (i = 1; i < PINSNUM; ++i) {
			wiringPiI2CWriteReg8(Cards[user_card_num].fd, GPIO_REG, 0x00);
			wiringPiI2CWriteReg8(Cards[user_card_num].fd, GPIO_REG, pinsArray[i]);
			// wait 1 second
			g_print("sound %d ", i);
			sleep(1);
		}
	}
	g_print("\nplayAllTest check end - %s was pressed\n", (gchar *)data);
}

/* 
 * 
 * 
 * utility functions 
 * 
 * 
 * 
 * */
void console_print(char *message) {
	/* print it to the console view */
	/* need append, deletes current text... */
	gtk_text_buffer_set_text(console_buffer, message, -1);
}