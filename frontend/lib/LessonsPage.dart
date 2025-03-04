import 'package:flutter/material.dart';
import 'FileDetailPage.dart';

class LessonsPage extends StatelessWidget {
  List<Map<String, String>> lessons = []; // Empty initially

  @override
  Widget build(BuildContext context) {
    double screenHeight = MediaQuery.of(context).size.height; // Get screen height

    return Scaffold(
      appBar: AppBar(title: Text("Lessons")),
      body: Padding(
        padding: const EdgeInsets.all(0.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (lessons.isEmpty)
              Padding(
                padding: EdgeInsets.only(top: screenHeight * 0.001, bottom: 16.0), 
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.arrow_back,
                      size: 24,
                      color: Colors.deepOrange,
                    ),
                    SizedBox(width: 8),
                    Flexible( // Ensures text adapts to screen size
                      child: Text(
                        "Make sure you have uploaded something here and start learning!",
                        style: TextStyle(fontSize: 16, fontStyle: FontStyle.italic),
                      ),
                    ),
                  ],
                ),
              ),

            Expanded(
              child: lessons.isEmpty
                  ? Center(
                      child: Padding(
                        padding: EdgeInsets.only(top: screenHeight * 0.1), // Adjust height dynamically
                        child: Text(
                          "No lessons created yet",
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    )
                  : ListView.builder(
                      itemCount: lessons.length,
                      itemBuilder: (context, index) {
                        final lesson = lessons[index];

                        return GestureDetector(
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => FileDetailPage(
                                    fileName: lesson['title'].toString() + '.pdf'),
                              ),
                            );
                          },
                          child: Card(
                            margin: EdgeInsets.symmetric(vertical: 8.0),
                            elevation: 3,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12.0),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(12.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    lesson['title']!,
                                    style: TextStyle(
                                        fontSize: 20, fontWeight: FontWeight.bold),
                                  ),
                                  SizedBox(height: 8),
                                  LayoutBuilder(
                                    builder: (context, constraints) {
                                      bool isNarrow = constraints.maxWidth < 300;

                                      return Wrap(
                                        alignment: WrapAlignment.spaceBetween,
                                        spacing: 8,
                                        runSpacing: 4,
                                        direction: isNarrow
                                            ? Axis.vertical
                                            : Axis.horizontal,
                                        children: [
                                          Text(
                                            "Test Date: ${lesson['date']!}",
                                            style: TextStyle(fontSize: 16),
                                          ),
                                          Text(
                                            "Difficulty: ${lesson['difficulty']!}",
                                            style: TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.w500),
                                          ),
                                        ],
                                      );
                                    },
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
