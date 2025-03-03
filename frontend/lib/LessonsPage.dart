// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'FileDetailPage.dart';
class LessonsPage extends StatelessWidget {
  final List<Map<String, String>> lessons = [
    //TODO create the link between LessonsPage (this) and MaterialsPage
    //TODO when there are no lessons created display a message
    {
      'title': '103A',
      'date': '2025-03-15',
      'difficulty': 'Hard',
    },
    {
      'title': 'Physics - Kinematics',
      'date': '2025-03-20',
      'difficulty': 'Medium',
    },
    {
      'title': 'History - WWII',
      'date': '2025-03-25',
      'difficulty': 'Easy',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Lessons")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView.builder(
          itemCount: lessons.length,
          itemBuilder: (context, index) {
            final lesson = lessons[index];

            return GestureDetector(
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    //TODO - MAPARE PE LECTIE - DOCUMENT 
                    builder: (context) => FileDetailPage(fileName: lesson['title'].toString() + '.pdf'),
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
                      // Lesson Title
                      Text(
                        lesson['title']!,
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 8),

                      // Test Date & Difficulty
                      LayoutBuilder(
                        builder: (context, constraints) {
                          bool isNarrow = constraints.maxWidth < 300;

                          return Wrap(
                            alignment: WrapAlignment.spaceBetween,
                            spacing: 8,
                            runSpacing: 4,
                            direction: isNarrow ? Axis.vertical : Axis.horizontal, // Adds spacing when wrapped
                            children: [
                              Text(
                                "Test Date: ${lesson['date']!}",
                                style: TextStyle(fontSize: 16),
                              ),
                              Text(
                                "Difficulty: ${lesson['difficulty']!}",
                                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
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
    );
  }
}

