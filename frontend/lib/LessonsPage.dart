// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'FileDetailPage.dart';

class LessonsPage extends StatefulWidget {
  @override
  _LessonsPageState createState() => _LessonsPageState();
}

class _LessonsPageState extends State<LessonsPage> {
  List<Map<String, String>> lessons = [];
  bool isLoading = true; // To show a loading indicator
  bool hasError = false; // To check if there's an error

  @override
  void initState() {
    super.initState();
    fetchLessons();
  }

  Future<void> fetchLessons() async {
    try {
      final response = await http.get(Uri.parse('http://10.0.2.2:5000/get_lessons'));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          lessons = List<Map<String, String>>.from(data['lessons']);
          isLoading = false;
        });
      } else {
        throw Exception('Failed to load lessons');
      }
    } catch (e) {
      setState(() {
        isLoading = false;
        hasError = true;
      });
    }
  }

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
                padding: EdgeInsets.only(top: screenHeight * 0.01, bottom: 10.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.arrow_back,
                      size: 20,
                      color: Colors.deepOrange,
                    ),
                    SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        "Check whether there are any materials to work on!",
                        style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                      ),
                    ),
                  ],
                ),
              ),

            // Loading Indicator
            if (isLoading)
              Expanded(
                child: Center(child: CircularProgressIndicator()),
              )

            // Error Message
            else if (hasError)
              Expanded(
                child: Center(
                  child: Text(
                    "No lessons created yet!",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                    textAlign: TextAlign.center,
                  ),
                ),
              )

            // No Lessons Message
            else if (lessons.isEmpty)
              Expanded(
                child: Center(
                  child: Padding(
                    padding: EdgeInsets.only(top: screenHeight * 0.1),
                    child: Text(
                      "No lessons created yet",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              )

            // Lessons List
            else
              Expanded(
                child: ListView.builder(
                  itemCount: lessons.length,
                  itemBuilder: (context, index) {
                    final lesson = lessons[index];

                    return GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => FileDetailPage(
                                fileName: '${lesson['title']}.pdf'),
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
                                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                              ),
                              SizedBox(height: 8),
                              LayoutBuilder(
                                builder: (context, constraints) {
                                  bool isNarrow = constraints.maxWidth < 300;

                                  return Wrap(
                                    alignment: WrapAlignment.spaceBetween,
                                    spacing: 8,
                                    runSpacing: 4,
                                    direction: isNarrow ? Axis.vertical : Axis.horizontal,
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
          ],
        ),
      ),
    );
  }
}
